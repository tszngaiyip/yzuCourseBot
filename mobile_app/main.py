import threading
import platform
import time
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.core.text import LabelBase, DEFAULT_FONT
from kivy.utils import get_color_from_hex

def setup_chinese_font():
    sys_name = platform.system()
    font_paths = []
    
    if sys_name == 'Windows':
        font_paths = [
            'C:/Windows/Fonts/msjh.ttc', # 微軟正黑體
            'C:/Windows/Fonts/msjh.ttf',
            'C:/Windows/Fonts/simsun.ttc', # 新細明體
            'C:/Windows/Fonts/simhei.ttf', # 黑體
        ]
    elif sys_name == 'Darwin': # macOS
        font_paths = [
            '/System/Library/Fonts/PingFang.ttc',
            '/System/Library/Fonts/STHeiti Light.ttc',
            '/Library/Fonts/Arial Unicode.ttf',
        ]
    elif sys_name == 'Linux':
        font_paths = [
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
            '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
        ]
    elif sys_name == 'Android':
        font_paths = [
            '/system/fonts/DroidSansFallback.ttf',
            '/system/fonts/NotoSansCJK-Regular.ttc',
        ]
        
    for path in font_paths:
        import os
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

from bot_core import CourseBot

setup_chinese_font()

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
        for style in self.theme_cls.font_styles.keys():
            self.theme_cls.font_styles[style][0] = "ChineseFont"

        
        self.bot = None
        self.bot_thread = None
        self.status_rows = {}
        
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
        
        self.acc_input = MDTextField(hint_text='學號 (Account)', mode="rectangle", font_name="ChineseFont", font_name_hint_text="ChineseFont")
        self.pwd_input = MDTextField(hint_text='密碼 (Password)', password=True, mode="rectangle", font_name="ChineseFont", font_name_hint_text="ChineseFont")
        
        login_card.add_widget(self.acc_input)
        login_card.add_widget(self.pwd_input)
        main_layout.add_widget(login_card)

        # === 課程清單卡片 ===
        courses_card = MDCard(orientation='vertical', padding=dp(20), spacing=dp(10), size_hint_y=None, elevation=2, radius=[dp(12)])
        courses_card.bind(minimum_height=courses_card.setter('height'))
        
        courses_card.add_widget(MDLabel(text="課程清單", font_style='Subtitle1', bold=True, size_hint_y=None, height=dp(24)))
        courses_card.add_widget(MDLabel(text="格式：部門代碼,課程代碼 (例: 312,EEB219A)", theme_text_color="Secondary", font_style='Caption', size_hint_y=None, height=dp(20)))
        
        self.courses_input = MDTextField(hint_text='每行一個，多筆請換行', multiline=True, mode="rectangle", max_height="150dp", font_name="ChineseFont", font_name_hint_text="ChineseFont")
        courses_card.add_widget(self.courses_input)
        main_layout.add_widget(courses_card)

        # === 動作按鈕列 ===
        action_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(15))
        self.delay_input = MDTextField(text='2.5', hint_text='延遲(秒)', size_hint_x=0.3, mode="rectangle", font_name="ChineseFont", font_name_hint_text="ChineseFont")
        
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

    def bot_status_callback(self, key, status):
        Clock.schedule_once(lambda dt: self.ui_update_status(key, status), 0)

    def bot_log_callback(self, msg):
        Clock.schedule_once(lambda dt: self.update_log(msg), 0)

    def bot_task(self, account, password, courses_str, delay):
        try:
            self.bot = CourseBot(
                account, password, 
                log_callback=self.bot_log_callback,
                status_callback=self.bot_status_callback
            )
            
            lines = [line.strip() for line in courses_str.split('\n') if line.strip()]
            if not lines:
                self.bot_log_callback("[color=#F44336]沒有輸入有效的課程代碼[/color]")
                return
            
            coursesList = lines
            
            # 初始化狀態列
            for course in coursesList:
                key = course.split(',')[1] if ',' in course else course
                self.bot_status_callback(key, "waiting")
            
            depts = set([i.split(',')[0] for i in coursesList if ',' in i])
            if not depts:
                self.bot_log_callback("[color=#F44336]課程代碼格式錯誤。[/color]")
                return

            self.bot_log_callback("=== 開始登入 ===")
            if self.bot.login():
                self.bot_log_callback("=== 登入成功，取得課程資料 ===")
                if self.bot.getCourseDB(depts):
                    self.bot_log_callback("=== 開始選課 ===")
                    self.bot.selectCourses(coursesList, delay)
            else:
                self.bot_log_callback("[color=#F44336]登入失敗，停止執行。[/color]")
        except Exception as e:
            self.bot_log_callback(f"[color=#F44336]發生未預期錯誤: {e}[/color]")
        finally:
            Clock.schedule_once(lambda dt: self.reset_ui(), 0)

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
        
        self.bot_thread = threading.Thread(target=self.bot_task, args=(account, password, courses, delay))
        self.bot_thread.daemon = True
        self.bot_thread.start()

    def stop_bot(self, instance):
        self.update_log("[color=#FF9800]收到停止要求，正在停止 Bot...[/color]")
        if self.bot:
            self.bot.running = False
        self.stop_btn.disabled = True

    def reset_ui(self):
        self.start_btn.disabled = False
        self.stop_btn.disabled = True
        self.acc_input.disabled = False
        self.pwd_input.disabled = False
        self.courses_input.disabled = False
        self.delay_input.disabled = False

if __name__ == '__main__':
    YzuBotApp().run()
