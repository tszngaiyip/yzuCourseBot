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
        
    if kivy_platform == 'win':
        font_paths.extend([
            'C:/Windows/Fonts/msjh.ttc',
            'C:/Windows/Fonts/msjh.ttf',
            'C:/Windows/Fonts/simsun.ttc',
            'C:/Windows/Fonts/simhei.ttf',
        ])
    elif kivy_platform == 'macosx':
        font_paths.extend([
            '/System/Library/Fonts/PingFang.ttc',
            '/System/Library/Fonts/STHeiti Light.ttc',
            '/Library/Fonts/Arial Unicode.ttf',
        ])
    elif kivy_platform == 'android':
        font_paths.extend([
            '/system/fonts/DroidSansFallback.ttf',
            '/system/fonts/NotoSansCJK-Regular.ttc',
        ])
    elif kivy_platform == 'linux':
        font_paths.extend([
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
            '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
        ])
        
    for path in font_paths:
        if os.path.exists(path):
            LabelBase.register(DEFAULT_FONT, path)
            LabelBase.register("ChineseFont", path)
            LabelBase.register("Roboto", path)
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

KV = '''
MDScreen:
    md_bg_color: "#F0F2F5"

    MDScreenManager:
        id: screen_manager

        MDScreen:
            name: "dashboard"

            MDScrollView:
                MDBoxLayout:
                    orientation: "vertical"
                    padding: "16dp"
                    spacing: "12dp"
                    adaptive_height: True

                    # 課程清單卡片
                    MDCard:
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

                        MDTextField:
                            id: courses_input
                            mode: "outlined"
                            multiline: True
                            size_hint_y: None
                            height: "120dp"
                            
                            MDTextFieldHintText:
                                text: "每行一個，多筆請換行"
                                font_name: "ChineseFont"

                    # 動作按鈕列
                    MDBoxLayout:
                        orientation: "horizontal"
                        adaptive_height: True
                        spacing: "12dp"

                        MDTextField:
                            id: delay_input
                            text: "2.5"
                            mode: "outlined"
                            size_hint_x: 0.3
                            
                            MDTextFieldHintText:
                                text: "延遲(秒)"
                                font_name: "ChineseFont"
                        
                        MDButton:
                            style: "filled"
                            theme_bg_color: "Custom"
                            md_bg_color: "#4CAF50"
                            size_hint_x: 0.45
                            on_release: app.start_bot()
                            disabled: False
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
                            disabled: True
                            on_release: app.stop_bot()
                            id: stop_btn
                            
                            MDButtonText:
                                id: stop_btn_text
                                text: "停止"
                                font_name: "ChineseFont"
                                theme_text_color: "Custom"
                                text_color: "#F44336"

                    # 狀態卡片
                    MDCard:
                        orientation: "vertical"
                        padding: "16dp"
                        spacing: "12dp"
                        adaptive_height: True
                        radius: [12]
                        line_color: "#E0E0E0"
                        md_bg_color: 1, 1, 1, 1
                        
                        MDLabel:
                            text: "選課狀態"
                            font_name: "ChineseFont"
                            adaptive_height: True
                            font_size: "16sp"
                            bold: True

                        MDScrollView:
                            size_hint_y: None
                            height: "180dp"
                            MDList:
                                id: status_list

                    # 日誌卡片
                    MDCard:
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
                            
                            MDButton:
                                style: "text"
                                on_release: app.clear_log()
                                MDButtonText:
                                    text: "清空日誌"
                                    font_name: "ChineseFont"
                                    
                        TextInput:
                            id: log_input
                            readonly: True
                            font_name: "ChineseFont"
                            background_color: 0.96, 0.96, 0.96, 1
                            foreground_color: 0.2, 0.2, 0.2, 1
                            size_hint_y: None
                            height: "150dp"
                            font_size: "13sp"

        MDScreen:
            name: "settings"
            
            MDScrollView:
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
                        
                    MDCard:
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
                            
                        MDTextField:
                            id: acc_input
                            mode: "outlined"
                            MDTextFieldLeadingIcon:
                                icon: "account"
                            MDTextFieldHintText:
                                text: "學號 (Account)"
                                font_name: "ChineseFont"
                                
                        MDTextField:
                            id: pwd_input
                            mode: "outlined"
                            password: True
                            MDTextFieldLeadingIcon:
                                icon: "lock"
                            MDTextFieldHintText:
                                text: "密碼 (Password)"
                                font_name: "ChineseFont"
                                
                    MDLabel:
                        text: "關於"
                        font_name: "ChineseFont"
                        font_size: "18sp"
                        bold: True
                        adaptive_height: True
                        
                    MDCard:
                        orientation: "vertical"
                        padding: "16dp"
                        spacing: "12dp"
                        adaptive_height: True
                        radius: [12]
                        line_color: "#E0E0E0"
                        md_bg_color: 1, 1, 1, 1
                        
                        MDLabel:
                            text: "版本: 2.0.0"
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
            active: True
            
            MDNavigationItemIcon:
                icon: "view-dashboard"
            MDNavigationItemLabel:
                text: "選課"
                font_name: "ChineseFont"
                
        MDNavigationItem:
            id: nav_settings
            
            MDNavigationItemIcon:
                icon: "cog"
            MDNavigationItemLabel:
                text: "設定"
                font_name: "ChineseFont"
'''

# ================= UI Components =================

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
        # 註冊中文字體 (不再需要去覆寫 theme_cls.font_styles，改用 font_name 屬性)
        setup_chinese_font()
        
        self.theme_cls.primary_palette = "Blue"

        self.status_rows = {}
        
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

        return Builder.load_string(KV)

    def on_switch_tabs(self, bar, item, item_icon, item_text):
        if item_text == "選課":
            self.root.ids.screen_manager.current = "dashboard"
        elif item_text == "設定":
            self.root.ids.screen_manager.current = "settings"

    def clear_log(self):
        if hasattr(self, 'root') and self.root:
            self.root.ids.log_input.text = ""

    def update_log(self, msg, *args):
        import re
        clean_msg = re.sub(r'\[/?(color|b)[^\]]*\]', '', msg)
        log_input = self.root.ids.log_input
        log_input.text += f'{clean_msg}\n'
        log_input.cursor = (0, len(log_input._lines))

    def ui_update_status(self, key, status):
        time_str = time.strftime("%H:%M:%S")
        if key in self.status_rows:
            self.status_rows[key].update(status, time_str)
        else:
            row = StatusRow(key)
            row.update(status, time_str)
            self.status_rows[key] = row
            self.root.ids.status_list.add_widget(row)

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
        self.status_rows.clear()
        
        self.bot_args = (account, password, courses, delay)
        self.update_log("[color=#2196F3]正在啟動背景服務並等待連線...[/color]")
        
        # 啟動 Android 服務 (若尚未啟動)
        self.start_android_service()
        
        self.ping_attempts = 0
        self.ping_event = Clock.schedule_interval(self._ping_service, 0.5)

    def stop_bot(self, *args):
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
