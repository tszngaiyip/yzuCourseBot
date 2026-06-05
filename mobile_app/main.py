import threading
import time
import sys
import traceback

def handle_exception(exc_type, exc_value, exc_traceback):
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print("FATAL ERROR:\n", error_msg)
    try:
        from kivy.app import App
        from kivy.uix.label import Label
        from kivy.uix.scrollview import ScrollView
        from kivy.core.window import Window
        Window.clearcolor = (0.8, 0.1, 0.1, 1)
        class CrashApp(App):
            def build(self):
                sv = ScrollView()
                lbl = Label(text=error_msg, font_size='12sp', halign='left', valign='top', size_hint_y=None, color=(1,1,1,1))
                lbl.bind(width=lambda *x: lbl.setter('text_size')(lbl, (lbl.width, None)))
                lbl.bind(texture_size=lbl.setter('size'))
                sv.add_widget(lbl)
                return sv
        app = App.get_running_app()
        if app:
            app.stop()
        CrashApp().run()
    except Exception as e:
        print("Crash Handler failed:", e)

sys.excepthook = handle_exception

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.core.text import LabelBase, DEFAULT_FONT
from kivy.utils import get_color_from_hex
from kivy.utils import platform as kivy_platform
def setup_chinese_font():
    import os
    font_paths = []
    
    local_font = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'NotoSansTC-Regular.otf')
    if os.path.exists(local_font):
        font_paths.append(local_font)
        
    for path in font_paths:
        if os.path.exists(path):
            LabelBase.register(DEFAULT_FONT, path)
            LabelBase.register("ChineseFont", path)
            LabelBase.register("Roboto", path)
            
            # Monkey-patch KivyMD's hint text positioning to compensate for NotoSansTC's larger line height
            from kivymd.uix.textfield.textfield import MDTextField
            from kivy.metrics import dp
            
            original_set_pos_hint_text = MDTextField.set_pos_hint_text
            
            def patched_set_pos_hint_text(self, y, x):
                # NotoSansTC has ~26% taller line height than Roboto (24px vs 19px @16sp).
                # KivyMD's positioning formulas are calibrated for Roboto, causing misalignment.
                if y > 0 and self._hint_text_label:
                    # Resting state: _hint_y = texture_height gives mathematically perfect centering.
                    # KivyMD's default (height/2 - texture_h/2) is off by 8px for NotoSansTC.
                    y = self._hint_text_label.texture_size[1]
                    original_set_pos_hint_text(self, round(y), x)
                else:
                    # Floating state: small offset to align text with border line.
                    if self.multiline:
                        # Delay calculation by one frame to ensure font_size and texture_size are updated.
                        def apply_multiline_floating(dt):
                            texture_height = self._hint_text_label.texture_size[1] if self._hint_text_label else dp(16)
                            # Align text with the top border gap, keeping it consistent with the with-text state.
                            target_y = -self.height / 2 + 1.5 * texture_height - dp(8)
                            original_set_pos_hint_text(self, round(target_y), x)
                        Clock.schedule_once(apply_multiline_floating)
                    else:
                        y += dp(2.5)
                # Round to integer to prevent subpixel rendering blurriness.
                        original_set_pos_hint_text(self, round(y), x)
                
            MDTextField.set_pos_hint_text = patched_set_pos_hint_text
            
            return True
            
    return False

from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.list import MDListItem, MDListItemHeadlineText, MDListItemSupportingText, MDListItemLeadingIcon
from kivy.uix.textinput import TextInput
from kivy.metrics import dp

from oscpy.client import OSCClient
from oscpy.server import OSCThreadServer
import os

class IOSBotWrapper:
    def __init__(self, app):
        self.app = app
        self.bot_instance = None
        self.bot_thread = None
        self.bg_sound = None

    def send_log(self, msg):
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: self.app.update_log(msg), 0)

    def send_status(self, key, status):
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: self.app.ui_update_status(key, status), 0)
        
    def start_bg_audio(self):
        from kivy.core.audio import SoundLoader
        if not self.bg_sound:
            sound_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "silent.wav")
            if os.path.exists(sound_path):
                self.bg_sound = SoundLoader.load(sound_path)
        if self.bg_sound:
            self.bg_sound.loop = True
            self.bg_sound.play()
            
    def stop_bg_audio(self):
        if self.bg_sound:
            self.bg_sound.stop()

    def bot_task(self, account, password, courses_str, delay):
        from bot_core import CourseBot
        try:
            self.start_bg_audio()
            self.bot_instance = CourseBot(
                account, password,
                log_callback=self.send_log,
                status_callback=self.send_status
            )
            lines = [line.strip() for line in courses_str.split('\n') if line.strip()]
            if not lines:
                self.send_log("[color=#F44336]沒有輸入有效的課程代碼[/color]")
                return
                
            coursesList = lines
            for course in coursesList:
                key = course.split(',')[1] if ',' in course else course
                self.send_status(key, "waiting")
            
            depts = set([i.split(',')[0] for i in coursesList if ',' in i])
            if not depts:
                self.send_log("[color=#F44336]課程代碼格式錯誤。[/color]")
                return

            self.send_log("[color=#2196F3]正在登入...[/color]")
            if self.bot_instance.login():
                self.send_log("[color=#2196F3]正在獲取課程資料...[/color]")
                if self.bot_instance.getCourseDB(depts):
                    self.send_log("[color=#4CAF50]開始選課...[/color]")
                    self.bot_instance.selectCourses(coursesList, delay)
                    self.send_log("[color=#4CAF50]選課流程結束！[/color]")
                else:
                    self.send_log("[color=#F44336]獲取課程資料失敗！[/color]")
            else:
                self.send_log("[color=#F44336]登入失敗！[/color]")
        except Exception as e:
            self.send_log(f"[color=#F44336]發生未預期錯誤: {e}[/color]")
        finally:
            self.send_log("[color=#FF9800]Bot 已經完全停止執行。[/color]")
            self.stop_bg_audio()
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt: self.app.reset_ui(), 0)

    def start(self, account, password, courses, delay):
        import threading
        if self.bot_instance and self.bot_instance.running:
            self.send_log("Bot 已經在執行中！")
            return
        self.bot_thread = threading.Thread(target=self.bot_task, args=(account, password, courses, delay))
        self.bot_thread.daemon = True
        self.bot_thread.start()
        
    def stop(self):
        self.send_log("[color=#FF9800]正在停止...[/color]")
        if self.bot_instance and self.bot_instance.running:
            self.bot_instance.running = False
        else:
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt: self.app.reset_ui(), 0)

KV = '''
MDBoxLayout:
    orientation: "vertical"
    md_bg_color: "#F0F2F5"

    MDScreenManager:
        id: screen_manager

        MDScreen:
            name: "dashboard"

            MDScrollView:
                do_scroll_x: False
                MDBoxLayout:
                    orientation: "vertical"
                    padding: "16dp"
                    spacing: "12dp"
                    adaptive_height: True

                    # 課程清單卡片
                    MDBoxLayout:
                        orientation: "vertical"
                        padding: "16dp"
                        spacing: "12dp"
                        adaptive_height: True
                        radius: [12]
                        line_color: "#E0E0E0"
                        md_bg_color: 1, 1, 1, 1
                        
                        MDLabel:
                            text: "課程清單"
                            font_name: "ChineseFont"
                            adaptive_height: True
                            font_size: "16sp"
                            bold: True

                        MDLabel:
                            text: "格式：部門代碼,課程代碼 (例: 312,EEB219A)"
                            font_name: "ChineseFont"
                            theme_text_color: "Custom"
                            text_color: "#757575"
                            adaptive_height: True
                            font_size: "13sp"

                        ScrollPassTextInput:
                            id: courses_input
                            mode: "outlined"
                            multiline: True
                            size_hint_y: None
                            height: max(self.minimum_height, dp(120))
                            font_name: "ChineseFont"
                            
                            MDTextFieldHintText:
                                text: "每行一個，多筆請換行"
                                font_name: "ChineseFont"

                    # 動作按鈕列
                    MDBoxLayout:
                        orientation: "horizontal"
                        adaptive_height: True
                        spacing: "12dp"

                        ScrollAwareTextField:
                            id: delay_input
                            text: "2.5"
                            mode: "outlined"
                            size_hint_x: 0.3
                            pos_hint: {"center_y": .5}
                            
                            MDTextFieldHintText:
                                text: "延遲(秒)"
                        
                        MDButton:
                            style: "filled"
                            theme_bg_color: "Custom"
                            md_bg_color: "#4CAF50"
                            size_hint_x: 0.45
                            pos_hint: {"center_y": .5}
                            on_release: app.start_bot()
                            disabled: False
                            ripple_effect: False
                            id: start_btn
                            
                            MDButtonText:
                                text: "開始選課"
                                font_name: "ChineseFont"
                                font_size: "16sp"
                        
                        MDButton:
                            style: "outlined"
                            theme_line_color: "Custom"
                            line_color: "#F44336"
                            size_hint_x: 0.25
                            pos_hint: {"center_y": .5}
                            disabled: True
                            ripple_effect: False
                            on_release: app.stop_bot()
                            id: stop_btn
                            
                            MDButtonText:
                                id: stop_btn_text
                                text: "停止"
                                font_name: "ChineseFont"
                                theme_text_color: "Custom"
                                text_color: "#F44336"

                    # 狀態卡片
                    MDBoxLayout:
                        orientation: "vertical"
                        padding: "16dp"
                        spacing: "12dp"
                        adaptive_height: True
                        radius: [12]
                        line_color: "#E0E0E0"
                        md_bg_color: 1, 1, 1, 1
                        
                        MDBoxLayout:
                            orientation: "horizontal"
                            adaptive_height: True
                            
                            MDLabel:
                                text: "選課狀態"
                                font_name: "ChineseFont"
                                adaptive_height: True
                                font_size: "16sp"
                                bold: True

                            # 新增：查看全部課程按鈕
                            MDButton:
                                style: "text"
                                on_release: app.show_full_status()
                                ripple_effect: False
                                MDButtonText:
                                    text: "全部課程"
                                    font_name: "ChineseFont"
                                    theme_text_color: "Custom"
                                    text_color: "#2196F3"

                        # 直接使用 MDBoxLayout，讓它自然排列，不再使用 NestedScrollView
                        MDBoxLayout:
                            adaptive_height: True
                            MDList:
                                id: status_list

                    # 日誌卡片
                    MDBoxLayout:
                        orientation: "vertical"
                        padding: "16dp"
                        spacing: "12dp"
                        adaptive_height: True
                        radius: [12]
                        line_color: "#E0E0E0"
                        md_bg_color: 1, 1, 1, 1

                        MDBoxLayout:
                            orientation: "horizontal"
                            adaptive_height: True
                            
                            MDLabel:
                                text: "執行日誌"
                                font_name: "ChineseFont"
                                font_size: "16sp"
                                bold: True
                                adaptive_height: True
                            
                            # 新增：查看完整日誌按鈕
                            MDButton:
                                style: "text"
                                on_release: app.show_full_log()
                                ripple_effect: False
                                MDButtonText:
                                    text: "全部日誌"
                                    font_name: "ChineseFont"
                                    theme_text_color: "Custom"
                                    text_color: "#2196F3"
                            
                            MDButton:
                                style: "text"
                                on_release: app.clear_log()
                                ripple_effect: False
                                MDButtonText:
                                    text: "清空"
                                    font_name: "ChineseFont"
                                    
                        # 移除 NestedScrollView，改用會自動適應高度的 MDBoxLayout
                        MDBoxLayout:
                            adaptive_height: True
                            padding: "8dp"
                            md_bg_color: "#F5F5F5"
                            radius: [8]
                            line_color: "#E0E0E0"
                            
                            MDLabel:
                                id: log_input
                                text: ""
                                markup: True
                                font_name: "ChineseFont"
                                font_size: "13sp"
                                theme_text_color: "Custom"
                                text_color: "#333333"
                                adaptive_height: True

        MDScreen:
            name: "settings"
            
            MDScrollView:
                do_scroll_x: False
                MDBoxLayout:
                    orientation: "vertical"
                    padding: "16dp"
                    spacing: "20dp"
                    adaptive_height: True
                    
                    MDLabel:
                        text: "帳號與登入設定"
                        font_name: "ChineseFont"
                        font_size: "18sp"
                        bold: True
                        adaptive_height: True
                        
                    MDBoxLayout:
                        orientation: "vertical"
                        padding: "16dp"
                        spacing: "12dp"
                        adaptive_height: True
                        radius: [12]
                        line_color: "#E0E0E0"
                        md_bg_color: 1, 1, 1, 1
                        
                        MDLabel:
                            text: "登入資訊"
                            font_name: "ChineseFont"
                            font_size: "16sp"
                            bold: True
                            adaptive_height: True
                            
                        MDLabel:
                            text: "安全起見，手機版不強制本機儲存，請輸入帳號密碼。"
                            font_name: "ChineseFont"
                            theme_text_color: "Custom"
                            text_color: "#757575"
                            font_size: "13sp"
                            adaptive_height: True
                            
                        ScrollAwareTextField:
                            id: acc_input
                            mode: "outlined"
                            
                            MDTextFieldLeadingIcon:
                                icon: "account"
                                
                            MDTextFieldHintText:
                                text: "學號 (Account)"
                                
                        ScrollAwareTextField:
                            id: pwd_input
                            mode: "outlined"
                            password: True
                            
                            MDTextFieldLeadingIcon:
                                icon: "lock"
                                
                            MDTextFieldHintText:
                                text: "密碼 (Password)"
                                
                    MDLabel:
                        text: "關於"
                        font_name: "ChineseFont"
                        font_size: "18sp"
                        bold: True
                        adaptive_height: True
                        
                    MDBoxLayout:
                        orientation: "vertical"
                        padding: "16dp"
                        spacing: "12dp"
                        adaptive_height: True
                        radius: [12]
                        line_color: "#E0E0E0"
                        md_bg_color: 1, 1, 1, 1
                        
                        MDLabel:
                            text: "版本: 2.0.3"
                            font_name: "ChineseFont"
                            font_size: "14sp"
                            adaptive_height: True
                            
                        MDLabel:
                            text: "作者: tsz7250"
                            font_name: "ChineseFont"
                            font_size: "14sp"
                            adaptive_height: True

    MDNavigationBar:
        on_switch_tabs: app.on_switch_tabs(*args)
        
        MDNavigationItem:
            id: nav_dashboard
            ripple_effect: False
            active: True
            
            MDNavigationItemIcon:
                icon: "view-dashboard"
            MDNavigationItemLabel:
                text: "選課"
                font_name: "ChineseFont"
                
        MDNavigationItem:
            id: nav_settings
            ripple_effect: False
            
            MDNavigationItemIcon:
                icon: "cog"
            MDNavigationItemLabel:
                text: "設定"
                font_name: "ChineseFont"
'''

# ================= UI Components =================
from kivy.properties import StringProperty, BooleanProperty, AliasProperty
from kivy.animation import Animation
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.textfield import MDTextField
from kivy.effects.scroll import ScrollEffect
from kivy.uix.scrollview import ScrollView
from kivy.uix.modalview import ModalView

class ScrollAwareTextField(MDTextField):
    def on_touch_move(self, touch):
        if touch.grab_current is self:
            distance_y = abs(touch.y - touch.oy)
            distance_x = abs(touch.x - touch.ox)
            # 若垂直滑動距離超過水平，且大於 5dp，判定為滾動畫面，取消文字選取
            if distance_y > dp(5) and distance_y > distance_x:
                self.cancel_selection()
                touch.ungrab(self)
                return False
        return super().on_touch_move(touch)

class ScrollPassTextInput(ScrollAwareTextField):
    def adjust_height(self, *args) -> None:
        pass

    def get_minimum_height(self):
        lines_count = max(1, len(self._lines))
        return self.line_height * lines_count + dp(24)

    minimum_height = AliasProperty(get_minimum_height, bind=['_lines', 'line_height'])

    def on_padding(self, instance, value):
        if hasattr(self, '_updating_padding') and self._updating_padding:
            return
            
        base_pad = dp(12) # Half of dp(24) from get_minimum_height
        extra_height = max(0, self.height - self.minimum_height)
        new_padding = [value[0], base_pad, value[2], base_pad + extra_height]
        
        if value != new_padding:
            self._updating_padding = True
            self.padding = new_padding
            self._updating_padding = False

class StatusRow(MDListItem):
    def __init__(self, key, **kwargs):
        super().__init__(**kwargs)
        self.headline = MDListItemHeadlineText(text=key, font_name="ChineseFont")
        self.supporting = MDListItemSupportingText(text="等待中", font_name="ChineseFont")
        self.leading_icon = MDListItemLeadingIcon(icon="clock-outline", theme_icon_color="Custom", icon_color=get_color_from_hex("#757575"))
        self.add_widget(self.leading_icon)
        self.add_widget(self.headline)
        self.add_widget(self.supporting)
        
    def update(self, status, time_str):
        colors_map = {
            "waiting": ("等待中", "#757575", "clock-outline"),
            "trying": ("嘗試中...", "#2196F3", "refresh"), 
            "success": ("已選上", "#4CAF50", "check-circle-outline"),
            "retry": ("重試中", "#FF9800", "reload"),
            "error": ("失敗", "#F44336", "alert-circle-outline")
        }
        
        text_status, hex_color, icon_name = colors_map.get(status, (status, "#1976D2", "information-outline"))
        
        self.supporting.text = f"{text_status} (最後更新: {time_str})"
        self.supporting.theme_text_color = "Custom"
        self.supporting.text_color = get_color_from_hex(hex_color)
        self.leading_icon.icon = icon_name
        self.leading_icon.icon_color = get_color_from_hex(hex_color)


class YzuBotApp(MDApp):
    def build(self):
        if kivy_platform != 'ios':
            Window.softinput_mode = "below_target"
        else:
            Window.softinput_mode = ""
        # 註冊中文字體 (不再需要去覆寫 theme_cls.font_styles，改用 font_name 屬性)
        setup_chinese_font()
        
        # 請求 Android 13+ 推播通知權限
        if kivy_platform == 'android':
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.POST_NOTIFICATIONS])
        
        self.theme_cls.primary_palette = "Blue"

        self.course_status_data = {}
        
        self.osc_server = OSCThreadServer()
        self.osc_server.listen('127.0.0.1', 3001, default=True)
        self.osc_server.bind(b'/log', self.osc_log_callback)
        self.osc_server.bind(b'/status', self.osc_status_callback)
        self.osc_server.bind(b'/done', self.osc_done_callback)
        self.osc_server.bind(b'/pong', self.osc_pong_callback)
        
        self.osc_client = OSCClient('127.0.0.1', 3000)
        self.ping_event = None
        self.bot_args = None
        self.ping_attempts = 0
        self.fallback_timer = None

        root_widget = Builder.load_string(KV)
        
        if kivy_platform == 'ios':
            from kivy.uix.screenmanager import NoTransition
            root_widget.ids.screen_manager.transition = NoTransition()
            
        return root_widget

    def on_switch_tabs(self, bar, item, item_icon, item_text):
        if kivy_platform == 'ios':
            from kivy.core.window import Window
            Window.release_all_keyboards()
            
        if item_text == "選課":
            self.root.ids.screen_manager.current = "dashboard"
        elif item_text == "設定":
            self.root.ids.screen_manager.current = "settings"

    def update_log(self, msg, *args):
        import re
        
        # 跳脫 Kivy markup 特殊字元
        safe_msg = msg.replace('&', '&amp;').replace('[', '&bl;').replace(']', '&br;')
        # 復原我們支援的標籤 (color, b)
        safe_msg = re.sub(r'&bl;(/?(?:color|b)[^&]*)&br;', r'[\1]', safe_msg)
        
        # 1. 儲存完整的歷史紀錄
        if not hasattr(self, 'full_log_history'):
            self.full_log_history = []
        self.full_log_history.append(safe_msg)
        
        # 2. 主畫面永遠只顯示最新的 3 筆日誌 (讓主畫面不會過長，維持排版乾淨)
        display_lines = self.full_log_history[-3:]
        if hasattr(self, 'root') and self.root:
            self.root.ids.log_input.text = '\n'.join(display_lines)
            
        # 3. 如果「全部日誌」的視窗正開著，即時新增標籤到清單中
        if hasattr(self, 'log_dialog_list') and getattr(self, 'log_dialog_list', None):
            from kivymd.uix.label import MDLabel
            lbl = MDLabel(
                text=safe_msg,
                markup=True,
                font_name="ChineseFont",
                font_size="13sp",
                theme_text_color="Custom",
                text_color="#333333",
                adaptive_height=True
            )
            self.log_dialog_list.add_widget(lbl)

    def clear_log(self):
        # 清空歷史紀錄
        if hasattr(self, 'full_log_history'):
            self.full_log_history.clear()
            
        # 清空主畫面文字
        if hasattr(self, 'root') and self.root:
            self.root.ids.log_input.text = ""
            
        # 如果視窗開著，也清空視窗內的元件
        if hasattr(self, 'log_dialog_list') and getattr(self, 'log_dialog_list', None):
            self.log_dialog_list.clear_widgets()

    def show_full_log(self):
        if not hasattr(self, 'full_log_history'):
            self.full_log_history = []
            
        # 建立一個專屬的浮動視窗佈局
        dialog_kv = '''
MDBoxLayout:
    orientation: "vertical"
    md_bg_color: "#F0F2F5"
    radius: [16, 16, 16, 16]
    padding: "16dp"
    spacing: "12dp"

    MDLabel:
        text: "歷史執行日誌"
        font_name: "ChineseFont"
        font_size: "18sp"
        bold: True
        adaptive_height: True

    # 專屬的捲動區塊，這裡不會跟主畫面打架
    MDBoxLayout:
        md_bg_color: "#F5F5F5"
        radius: [8]
        line_color: "#E0E0E0"
        padding: "8dp"
        
        MDScrollView:
            do_scroll_x: False
            MDBoxLayout:
                id: full_log_list
                orientation: 'vertical'
                adaptive_height: True
                spacing: "4dp"

    MDButton:
        style: "filled"
        pos_hint: {"center_x": .5}
        on_release: app.close_full_log()
        ripple_effect: False
        MDButtonText:
            text: "關閉視窗"
            font_name: "ChineseFont"
'''
        # 使用 Kivy 原生且最穩定的 ModalView 產生彈出視窗
        self.log_dialog = ModalView(
            size_hint=(0.9, 0.8), # 佔據螢幕 90% 寬, 80% 高
            background_color=(0, 0, 0, 0.7) # 背景半透明變暗
        )
        
        from kivy.lang import Builder
        from kivymd.uix.label import MDLabel
        content = Builder.load_string(dialog_kv)
        
        # 儲存容器的參照，以便新日誌進來時能即時更新
        self.log_dialog_list = content.ids.full_log_list
        
        # 將現有日誌建立元件並加入清單中
        for msg in self.full_log_history:
            lbl = MDLabel(
                text=msg,
                markup=True,
                font_name="ChineseFont",
                font_size="13sp",
                theme_text_color="Custom",
                text_color="#333333",
                adaptive_height=True
            )
            self.log_dialog_list.add_widget(lbl)
        
        self.log_dialog.add_widget(content)
        self.log_dialog.open()

    def get_full_log_text(self):
        if not hasattr(self, 'full_log_history'):
            return ""
        return '\n'.join(self.full_log_history)

    def close_full_log(self):
        if hasattr(self, 'log_dialog') and self.log_dialog:
            self.log_dialog.dismiss()
            self.log_dialog_list = None

    def ui_update_status(self, key, status):
        time_str = time.strftime("%H:%M:%S")
        
        if not hasattr(self, 'course_status_data'):
            self.course_status_data = {}
            
        self.course_status_data[key] = (status, time_str)
        
        # 1. 更新主畫面的前 3 筆
        main_keys = list(self.course_status_data.keys())[:3]
        
        self.root.ids.status_list.clear_widgets()
        for k in main_keys:
            row = StatusRow(k)
            row.update(*self.course_status_data[k])
            self.root.ids.status_list.add_widget(row)
            
        # 2. 如果 Modal 視窗開著，更新視窗內的所有清單
        if hasattr(self, 'status_dialog_list') and getattr(self, 'status_dialog_list', None):
            self.status_dialog_list.clear_widgets()
            for k in self.course_status_data.keys():
                row = StatusRow(k)
                row.update(*self.course_status_data[k])
                self.status_dialog_list.add_widget(row)

    def show_full_status(self):
        if not hasattr(self, 'course_status_data'):
            self.course_status_data = {}
            
        # 建立一個專屬的浮動視窗佈局
        dialog_kv = '''
MDBoxLayout:
    orientation: "vertical"
    md_bg_color: "#F0F2F5"
    radius: [16, 16, 16, 16]
    padding: "16dp"
    spacing: "12dp"

    MDLabel:
        text: "全部選課狀態"
        font_name: "ChineseFont"
        font_size: "18sp"
        bold: True
        adaptive_height: True

    # 專屬的捲動區塊
    MDScrollView:
        do_scroll_x: False
        MDBoxLayout:
            adaptive_height: True
            MDList:
                id: full_status_list

    MDButton:
        style: "filled"
        pos_hint: {"center_x": .5}
        on_release: app.close_full_status()
        ripple_effect: False
        MDButtonText:
            text: "關閉視窗"
            font_name: "ChineseFont"
'''
        self.status_dialog = ModalView(
            size_hint=(0.9, 0.8),
            background_color=(0, 0, 0, 0.7)
        )
        
        from kivy.lang import Builder
        content = Builder.load_string(dialog_kv)
        self.status_dialog_list = content.ids.full_status_list
        
        # 渲染所有的狀態
        for k in self.course_status_data.keys():
            row = StatusRow(k)
            row.update(*self.course_status_data[k])
            self.status_dialog_list.add_widget(row)
            
        self.status_dialog.add_widget(content)
        self.status_dialog.open()

    def close_full_status(self):
        if hasattr(self, 'status_dialog') and getattr(self, 'status_dialog', None):
            self.status_dialog.dismiss()
            self.status_dialog_list = None

    def osc_status_callback(self, key_b, status_b):
        key = key_b.decode('utf-8')
        status = status_b.decode('utf-8')
        Clock.schedule_once(lambda dt: self.ui_update_status(key, status), 0)

    def osc_log_callback(self, msg_b):
        msg = msg_b.decode('utf-8')
        Clock.schedule_once(lambda dt: self.update_log(msg), 0)

    def osc_done_callback(self):
        Clock.schedule_once(lambda dt: self.reset_ui(), 0)

    def osc_pong_callback(self):
        Clock.schedule_once(lambda dt: self.handle_pong(), 0)

    def handle_pong(self):
        if self.ping_event:
            self.ping_event.cancel()
            self.ping_event = None
            self.update_log("[color=#4CAF50]背景服務已連線！發送執行指令...[/color]")
            
            if self.bot_args:
                account, password, courses, delay = self.bot_args
                try:
                    self.osc_client.send_message(
                        b'/start', 
                        [account.encode('utf-8'), password.encode('utf-8'), courses.encode('utf-8'), delay]
                    )
                except Exception as e:
                    self.update_log(f"無法與背景服務通訊: {e}")
                    self.reset_ui()

    def _ping_service(self, dt):
        self.ping_attempts += 1
        if self.ping_attempts > 10:
            self.update_log("[color=#F44336]無法連線到背景服務 (超時)。請重試。[/color]")
            if self.ping_event:
                self.ping_event.cancel()
                self.ping_event = None
            self.reset_ui()
            return
            
        try:
            self.osc_client.send_message(b'/ping', [])
        except:
            pass

    def start_android_service(self):
        if kivy_platform == 'android':
            try:
                from jnius import autoclass
                service = autoclass("org.yzu.yzucoursebot.ServiceBotservice")
                mActivity = autoclass("org.kivy.android.PythonActivity").mActivity
                argument = ""
                service.start(mActivity, argument)
            except Exception as e:
                self.update_log(f"啟動服務失敗: {e}")

    def start_bot(self, *args):
        account = self.root.ids.acc_input.text.strip()
        password = self.root.ids.pwd_input.text.strip()
        courses = self.root.ids.courses_input.text.strip()
        try:
            delay = float(self.root.ids.delay_input.text.strip())
        except:
            delay = 2.5

        if not account or not password:
            self.update_log("[color=#F44336]請輸入帳號與密碼！[/color]")
            return

        self.root.ids.start_btn.disabled = True
        self.root.ids.stop_btn.disabled = False
        self.root.ids.acc_input.disabled = True
        self.root.ids.pwd_input.disabled = True
        self.root.ids.courses_input.disabled = True
        self.root.ids.delay_input.disabled = True
        
        # 清除舊的狀態
        self.root.ids.status_list.clear_widgets()
        if hasattr(self, 'course_status_data'):
            self.course_status_data.clear()
        if hasattr(self, 'status_dialog_list') and getattr(self, 'status_dialog_list', None):
            self.status_dialog_list.clear_widgets()
            
        if kivy_platform != 'android':
            if not hasattr(self, 'ios_wrapper'):
                self.ios_wrapper = IOSBotWrapper(self)
            self.update_log("[color=#2196F3]正在啟動本機選課程序...[/color]")
            self.ios_wrapper.start(account, password, courses, delay)
            return
        
        self.bot_args = (account, password, courses, delay)
        self.update_log("[color=#2196F3]正在啟動背景服務並等待連線...[/color]")
        
        # 啟動 Android 服務 (若尚未啟動)
        self.start_android_service()
        
        self.ping_attempts = 0
        self.ping_event = Clock.schedule_interval(self._ping_service, 0.5)

    def stop_bot(self, *args):
        if kivy_platform != 'android':
            if hasattr(self, 'ios_wrapper'):
                self.ios_wrapper.stop()
            self.root.ids.stop_btn.disabled = True
            if getattr(self, 'fallback_timer', None):
                self.fallback_timer.cancel()
            self.fallback_timer = Clock.schedule_once(self.force_reset_ui, 15)
            return

        self.update_log("[color=#FF9800]傳送停止指令到背景服務...[/color]")
        try:
            self.osc_client.send_message(b'/stop', [])
        except Exception as e:
            self.update_log(f"無法與背景服務通訊: {e}")
        self.root.ids.stop_btn.disabled = True

        if getattr(self, 'fallback_timer', None):
            self.fallback_timer.cancel()
        self.fallback_timer = Clock.schedule_once(self.force_reset_ui, 15)

    def force_reset_ui(self, dt):
        self.fallback_timer = None
        if self.root.ids.stop_btn.disabled and not self.root.ids.start_btn.disabled:
            return
        self.update_log("[color=#F44336]警告：等候背景服務逾時，強制解除鎖定！[/color]")
        self.reset_ui()

    def reset_ui(self):
        if getattr(self, 'fallback_timer', None):
            self.fallback_timer.cancel()
            self.fallback_timer = None

        if hasattr(self, 'root') and self.root:
            self.root.ids.start_btn.disabled = False
            self.root.ids.stop_btn.disabled = True
            self.root.ids.acc_input.disabled = False
            self.root.ids.pwd_input.disabled = False
            self.root.ids.courses_input.disabled = False
            self.root.ids.delay_input.disabled = False

if __name__ == '__main__':
    YzuBotApp().run()
