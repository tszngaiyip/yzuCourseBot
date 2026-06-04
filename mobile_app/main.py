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

# ================= KivyMD Imports =================
from kivymd.app import MDApp
from kivymd.uix.card import MDCard
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.list import MDList, TwoLineListItem
from kivy.metrics import dp

from oscpy.client import OSCClient
from oscpy.server import OSCThreadServer
import os

# ================= UI Components =================

class StatusRow(TwoLineListItem):
    def __init__(self, key, **kwargs):
        super().__init__(**kwargs)
        self.text = f"[b]{key}[/b]"
        self.secondary_text = "等待中"
        
    def update(self, status, time_str):
        colors_map = {
            "waiting": ("等待中", "Secondary"),
            "trying": ("嘗試中...", "Custom"), 
            "success": ("已選上", "Custom"),
            "retry": ("重試中", "Custom"),
            "error": ("失敗", "Error")
        }
        
        text_status, theme_col = colors_map.get(status, (status, "Primary"))
        
        hex_colors = {
            "trying": "#2196F3",
            "success": "#4CAF50",
            "retry": "#FF9800"
        }
        
        if theme_col == "Custom":
            self.secondary_theme_text_color = "Custom"
            self.secondary_text_color = get_color_from_hex(hex_colors.get(status, "#000000"))
        else:
            self.secondary_theme_text_color = theme_col
            
        self.secondary_text = f"{text_status} (最後更新: {time_str})"


class YzuBotApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        Window.clearcolor = get_color_from_hex('#F0F2F5')
        
        # 覆寫 KivyMD 預設字體為中文字體
        font_registered = setup_chinese_font()
        if font_registered:
            for style in self.theme_cls.font_styles.keys():
                self.theme_cls.font_styles[style][0] = "ChineseFont"

        
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
        
        root_scroll = MDScrollView()
        main_layout = MDBoxLayout(orientation='vertical', padding=dp(20), spacing=dp(20), size_hint_y=None)
        main_layout.bind(minimum_height=main_layout.setter('height'))
        
        # Header
        header = MDLabel(text='YZU Course Bot', font_style='H5', bold=True, size_hint_y=None, height=dp(40), halign="center")
        main_layout.add_widget(header)
        
        # === 登入卡片 ===
        login_card = MDCard(orientation='vertical', padding=dp(20), spacing=dp(10), size_hint_y=None, elevation=2, radius=[dp(12)])
        login_card.bind(minimum_height=login_card.setter('height'))
        
        login_card.add_widget(MDLabel(text="登入資訊", font_style='Subtitle1', bold=True, size_hint_y=None, height=dp(24)))
        login_card.add_widget(MDLabel(text="安全起見，手機版不強制本機儲存，請輸入帳號密碼。", theme_text_color="Secondary", font_style='Caption', size_hint_y=None, height=dp(20)))
        
        self.acc_input = MDTextField(hint_text='學號 (Account)', mode="rectangle", font_name="ChineseFont")
        self.pwd_input = MDTextField(hint_text='密碼 (Password)', password=True, mode="rectangle", font_name="ChineseFont")
        
        login_card.add_widget(self.acc_input)
        login_card.add_widget(self.pwd_input)
        main_layout.add_widget(login_card)

        # === 課程清單卡片 ===
        courses_card = MDCard(orientation='vertical', padding=dp(20), spacing=dp(10), size_hint_y=None, elevation=2, radius=[dp(12)])
        courses_card.bind(minimum_height=courses_card.setter('height'))
        
        courses_card.add_widget(MDLabel(text="課程清單", font_style='Subtitle1', bold=True, size_hint_y=None, height=dp(24)))
        courses_card.add_widget(MDLabel(text="格式：部門代碼,課程代碼 (例: 312,EEB219A)", theme_text_color="Secondary", font_style='Caption', size_hint_y=None, height=dp(20)))
        
        self.courses_input = MDTextField(hint_text='每行一個，多筆請換行', multiline=True, mode="rectangle", max_height="150dp", font_name="ChineseFont")
        courses_card.add_widget(self.courses_input)
        main_layout.add_widget(courses_card)

        # === 動作按鈕列 ===
        action_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(15))
        self.delay_input = MDTextField(text='2.5', hint_text='延遲(秒)', size_hint_x=0.3, mode="rectangle", font_name="ChineseFont")
        
        self.start_btn = MDRaisedButton(text='開始選課', size_hint_x=0.45, md_bg_color=self.theme_cls.primary_color, font_size="16sp")
        self.start_btn.bind(on_press=self.start_bot)
        
        self.stop_btn = MDFlatButton(text='停止', size_hint_x=0.25, disabled=True, theme_text_color="Error")
        self.stop_btn.bind(on_press=self.stop_bot)

        action_layout.add_widget(self.delay_input)
        action_layout.add_widget(self.start_btn)
        action_layout.add_widget(self.stop_btn)
        main_layout.add_widget(action_layout)

        # === 狀態卡片 ===
        status_card = MDCard(orientation='vertical', padding=dp(20), spacing=dp(10), size_hint_y=None, elevation=2, radius=[dp(12)])
        status_card.bind(minimum_height=status_card.setter('height'))
        status_card.add_widget(MDLabel(text="選課狀態", font_style='Subtitle1', bold=True, size_hint_y=None, height=dp(24)))
        
        self.status_scroll = MDScrollView(size_hint_y=None, height=dp(180))
        self.status_list = MDList()
        self.status_scroll.add_widget(self.status_list)
        status_card.add_widget(self.status_scroll)
        
        main_layout.add_widget(status_card)

        # === 日誌卡片 ===
        log_card = MDCard(orientation='vertical', padding=dp(20), spacing=dp(10), size_hint_y=None, elevation=2, radius=[dp(12)])
        log_card.bind(minimum_height=log_card.setter('height'))
        
        log_header = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(30))
        log_title = MDLabel(text="執行日誌", font_style='Subtitle1', bold=True)
        log_clear = MDFlatButton(text="清空日誌", on_press=self.clear_log)
        
        log_header.add_widget(log_title)
        log_header.add_widget(log_clear)
        log_card.add_widget(log_header)

        self.log_scroll = MDScrollView(size_hint_y=None, height=dp(150))
        self.log_label = MDLabel(text='', theme_text_color="Secondary", size_hint_y=None, valign='top', markup=True)
        self.log_label.bind(width=lambda *x: self.log_label.setter('text_size')(self.log_label, (self.log_label.width, None)))
        self.log_label.bind(texture_size=self.log_label.setter('size'))
        
        self.log_scroll.add_widget(self.log_label)
        log_card.add_widget(self.log_scroll)
        
        main_layout.add_widget(log_card)

        root_scroll.add_widget(main_layout)
        return root_scroll

    def clear_log(self, instance):
        self.log_label.text = ""

    def update_log(self, msg, *args):
        self.log_label.text += f'{msg}\n'
        Clock.schedule_once(lambda dt: setattr(self.log_scroll, 'scroll_y', 0), 0.1)

    def ui_update_status(self, key, status):
        time_str = time.strftime("%H:%M:%S")
        if key in self.status_rows:
            self.status_rows[key].update(status, time_str)
        else:
            row = StatusRow(key)
            row.update(status, time_str)
            self.status_rows[key] = row
            self.status_list.add_widget(row)

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

    def start_bot(self, instance):
        account = self.acc_input.text.strip()
        password = self.pwd_input.text.strip()
        courses = self.courses_input.text.strip()
        try:
            delay = float(self.delay_input.text.strip())
        except:
            delay = 2.5

        if not account or not password:
            self.update_log("[color=#F44336]請輸入帳號與密碼！[/color]")
            return

        self.start_btn.disabled = True
        self.stop_btn.disabled = False
        self.acc_input.disabled = True
        self.pwd_input.disabled = True
        self.courses_input.disabled = True
        self.delay_input.disabled = True
        
        # 清除舊的狀態
        self.status_list.clear_widgets()
        self.status_rows.clear()
        
        self.bot_args = (account, password, courses, delay)
        self.update_log("[color=#2196F3]正在啟動背景服務並等待連線...[/color]")
        
        # 啟動 Android 服務 (若尚未啟動)
        self.start_android_service()
        
        self.ping_attempts = 0
        self.ping_event = Clock.schedule_interval(self._ping_service, 0.5)

    def stop_bot(self, instance):
        self.update_log("[color=#FF9800]傳送停止指令到背景服務...[/color]")
        try:
            self.osc_client.send_message(b'/stop', [])
        except Exception as e:
            self.update_log(f"無法與背景服務通訊: {e}")
        self.stop_btn.disabled = True

        if getattr(self, 'fallback_timer', None):
            self.fallback_timer.cancel()
        self.fallback_timer = Clock.schedule_once(self.force_reset_ui, 15)

    def force_reset_ui(self, dt):
        self.fallback_timer = None
        if self.stop_btn.disabled and not self.start_btn.disabled:
            return
        self.update_log("[color=#F44336]警告：等候背景服務逾時，強制解除鎖定！[/color]")
        self.reset_ui()

    def reset_ui(self):
        if getattr(self, 'fallback_timer', None):
            self.fallback_timer.cancel()
            self.fallback_timer = None

        self.start_btn.disabled = False
        self.stop_btn.disabled = True
        self.acc_input.disabled = False
        self.pwd_input.disabled = False
        self.courses_input.disabled = False
        self.delay_input.disabled = False

if __name__ == '__main__':
    YzuBotApp().run()
