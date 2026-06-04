import flet as ft
import os
import sys
import time
import tempfile
import requests
import configparser
from threading import Thread, Event
from bs4 import BeautifulSoup
from multiprocessing import freeze_support

# 注意：numpy 和 cv2 移至懶加載，只在需要驗證碼時才 import

# 修復 PyInstaller 打包後 sys.stdout 和 sys.stderr 為 None 的問題
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')

# 獲取資源檔案的正確路徑（支援 PyInstaller 打包）
def resource_path(relative_path):
    """取得資源檔案的絕對路徑，支援開發環境和 PyInstaller 打包後的環境"""
    try:
        # PyInstaller 創建的臨時資料夾路徑
        base_path = sys._MEIPASS
    except AttributeError:
        # 開發環境中使用當前目錄，如果是從 GUI 目錄執行，則返回上一層目錄
        base_path = os.path.abspath(".")
        if os.path.basename(base_path) == "GUI":
            base_path = os.path.dirname(base_path)
    return os.path.join(base_path, relative_path)

class CourseBot:
    def __init__(self, account, password, log_callback=None, status_callback=None, stop_event=None):
        self.account = account
        self.password = password
        self.coursesDB = {}
        self.log_callback = log_callback
        self.status_callback = status_callback
        self.stop_event = stop_event or Event()
        
        # captcha.png 存放在系統暫存目錄
        self.captcha_path = os.path.join(tempfile.gettempdir(), 'yzuCourseBot_captcha.png')

        # 移至載入 TensorFlow 模型，等到需要時才加載
        self.model = None        
        self.n_classes = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'

        # for requests
        self.session = requests.Session()
        self.session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36'

        self.loginUrl = 'https://isdna1.yzu.edu.tw/CnStdSel/Index.aspx'
        self.captchaUrl = 'https://isdna1.yzu.edu.tw/CnStdSel/SelRandomImage.aspx'
        self.courseListUrl = 'https://isdna1.yzu.edu.tw/CnStdSel/SelCurr/CosList.aspx'
        self.courseSelectUrl = 'https://isdna1.yzu.edu.tw/CnStdSel/SelCurr/CurrMainTrans.aspx?mSelType=SelCos&mUrl='

        self.loginPayLoad = {
            '__VIEWSTATE': '',
            '__VIEWSTATEGENERATOR': '',
            '__EVENTVALIDATION': '',
            'DPL_SelCosType': '',
            'Txt_User': self.account,
            'Txt_Password': self.password,
            'Txt_CheckCode': '',
            'btnOK': '確定'
        }

        self.selectPayLoad = {}

    def _load_model(self):
        """懶載入 ONNX Runtime 模型，等到真正需要時才 import 相關套件"""
        if self.model is None:
            # 現在才 import NumPy, cv2 和 onnxruntime（懶載入）
            import numpy as np
            import cv2
            import onnxruntime as ort

            # 保存 numpy 和 cv2 到 instance，供其他方法使用
            self.np = np
            self.cv2 = cv2
            self.ort = ort

            model_path = resource_path('model.onnx')
            self.model = ort.InferenceSession(model_path)
            self.log("ONNX 模型載入完成")

    def predict(self, img):
        # 確保模型已載入
        self._load_model()
        
        input_name = self.model.get_inputs()[0].name
        output_names = [o.name for o in self.model.get_outputs()]
        
        # 執行預測
        prediction = self.model.run(output_names, {input_name: self.np.array([img], dtype=self.np.float32)})

        predicStr = ""
        for pred in prediction:
            predicStr += self.n_classes[self.np.argmax(pred[0])]
        return predicStr

    def captchaOCR(self):
        # 確保模型已載入（這樣才能使用 cv2）
        self._load_model()
        captchaImg = self.cv2.imread(self.captcha_path) / 255.0
        return self.predict(captchaImg)

    # login into system and get session
    def login(self):
        
        while True:
            # 檢查是否需要停止
            if self.stop_event.is_set():
                self.log("使用者已停止")
                return False
            
            # clear Session object
            self.session.cookies.clear()

            # download and recognize captch
            with self.session.get(self.captchaUrl, stream= True) as captchaHtml:
                with open(self.captcha_path, 'wb') as img:
                    img.write(captchaHtml.content)
            captcha = self.captchaOCR()

            # get login data
            loginHtml = self.session.get(self.loginUrl)
            
            # check if system is open
            if '選課系統尚未開放!' in loginHtml.text:
                self.log('選課系統尚未開放!')
                # 檢查是否需要停止
                if self.stop_event.is_set():
                    self.log("使用者已停止")
                    return False
                continue

            # use BeautifulSoup to parse html
            parser = BeautifulSoup(loginHtml.text, 'lxml')

            # update login payload
            self.loginPayLoad['__VIEWSTATE'] = parser.select("#__VIEWSTATE")[0]['value']
            self.loginPayLoad['__VIEWSTATEGENERATOR'] = parser.select("#__VIEWSTATEGENERATOR")[0]['value']
            self.loginPayLoad['__EVENTVALIDATION'] = parser.select("#__EVENTVALIDATION")[0]['value']
            self.loginPayLoad['DPL_SelCosType'] = parser.select("#DPL_SelCosType option")[1]['value']
            self.loginPayLoad['Txt_CheckCode'] = captcha

            result = self.session.post(self.loginUrl, data= self.loginPayLoad)
            if ("parent.location ='SelCurr.aspx?Culture=zh-tw'" in result.text): #成功登入訊息可能一直改，挑個不太能改的
                self.log('Login Successful! {}'.format(captcha))
                break
            elif ("資料庫發生異常" in result.text): # 僅比較成功登入及帳號密碼錯誤的訊息，不確定是否還有其他種情況也符合這個條件
                self.log('帳號或密碼錯誤，請重新確認。')
            elif ("您未在此階段選課時程之內!請於時程內選課!!" in result.text):
                self.log('您未在此階段選課時程之內!請於時程內選課!!')
            else:
                self.log("Login Failed, Re-try!")
                # 檢查是否需要停止
                if self.stop_event.is_set():
                    self.log("使用者已停止")
                    return False
                continue
            return False  # Login failed with error

        return True  # Login successful

    def getCourseDB(self, depts):

        for dept in depts:
            # use BeautifulSoup to parse html
            html = self.session.get(self.courseListUrl)
            if "異常登入" in html.text:
                self.log("異常登入，休息10分鐘!")
                time.sleep(600) # sleep 10 min
                continue
            parser = BeautifulSoup(html.text, 'lxml')

            self.selectPayLoad[dept] = {
                '__EVENTTARGET': 'DPL_Degree',
                '__EVENTARGUMENT': '',
                '__LASTFOCUS': '',
                '__VIEWSTATE': parser.select("#__VIEWSTATE")[0]['value'],
                '__VIEWSTATEGENERATOR': parser.select("#__VIEWSTATEGENERATOR")[0]['value'],
                '__VIEWSTATEENCRYPTED': '',
                '__EVENTVALIDATION': parser.select("#__EVENTVALIDATION")[0]['value'],
                'Hidden1': '',
                'Hid_SchTime': '',
                'DPL_DeptName': dept,
                'DPL_Degree': '6',
            }

            # use BeautifulSoup to parse html
            html = self.session.post(self.courseListUrl, data= self.selectPayLoad[dept])
            if "Error" in html.text:
                self.log('Wrong coursesList, please check it again!')
                return False
            parser = BeautifulSoup(html.text, 'lxml')

            # parse and save courses information
            courseList = parser.select("#CosListTable input")
            for courseInfo in courseList:
                tokens = courseInfo.attrs['name'].split(',') # SelCos,CS354,A,1,F,3,Y,Chinese,CS354,A,3 電腦與網路安全概論

                key = tokens[1] + tokens[2]
                courseName = '{} {}'.format(key, tokens[-1].split(' ')[1])

                self.coursesDB[key] = {
                    'name': courseName,
                    'mUrl': courseInfo.attrs['name']
                }
                # self.log(self.coursesDB[key])

            self.log('Get {} Data Completed!'.format(dept))

        return True


    def selectCourses(self, coursesList, delay = 0):
        while len(coursesList) > 0:
            # 檢查是否需要停止
            if self.stop_event.is_set():
                self.log("使用者已停止選課")
                return
                
            for course in coursesList.copy():
                # 檢查是否需要停止
                if self.stop_event.is_set():
                    self.log("使用者已停止選課")
                    return
                    
                tokens = course.split(',')
                dept = tokens[0]
                key  = tokens[1]
                
                # 更新狀態為嘗試中
                if self.status_callback:
                    self.status_callback(key, "trying")
                
                # check if the classID is legal
                if key not in self.coursesDB:
                    self.log('{} is not a legal classID'.format(key))
                    coursesList.remove(course)
                    if self.status_callback:
                        self.status_callback(key, "error")
                    continue
                
                # simulte click button
                html = self.session.post(self.courseListUrl, data= self.selectPayLoad[dept])
                parser = BeautifulSoup(html.text, 'lxml')

                selectPayLoad = {
                    '__EVENTTARGET': '',
                    '__EVENTARGUMENT': '',
                    '__LASTFOCUS': '',
                    '__VIEWSTATE': parser.select("#__VIEWSTATE")[0]['value'],
                    '__VIEWSTATEGENERATOR': parser.select("#__VIEWSTATEGENERATOR")[0]['value'],
                    '__VIEWSTATEENCRYPTED': '',
                    '__EVENTVALIDATION': parser.select("#__EVENTVALIDATION")[0]['value'],
                    'Hidden1': '',
                    'Hid_SchTime': '',
                    'DPL_DeptName': dept,
                    'DPL_Degree': '6',
                    self.coursesDB[key]['mUrl'] + '.x': '0', 
                    self.coursesDB[key]['mUrl'] + '.y': '0'
                }
                self.session.post(self.courseListUrl, data= selectPayLoad)

                # select course
                html = self.session.get(self.courseSelectUrl + self.coursesDB[key]['mUrl'] + ' ,B,')

                # check if successful
                parser = BeautifulSoup(html.text, 'lxml')
                alertMsg = parser.select("script")[0].string.split(';')[0]
                self.log('{} {}'.format(self.coursesDB[key]['name'], alertMsg[7:-2]))

                if "加選訊息：" in alertMsg or "已選過" in alertMsg:
                    coursesList.remove(course)
                    if self.status_callback:
                        self.status_callback(key, "success")
                elif "please log on again!" in alertMsg:
                    if not self.login():
                        return
                else:
                    # 重試中
                    if self.status_callback:
                        self.status_callback(key, "retry")

                time.sleep(delay)

    def log(self, msg):
        timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]", time.localtime())
        full_msg = f"{timestamp} {msg}"
        print(full_msg)
        if self.log_callback:
            self.log_callback(full_msg)

def main(page: ft.Page):
    # 設定頁面屬性
    page.title = "元智大學選課機器人"
    page.window.width = 480
    page.window.height = 950
    page.window.min_width = 480
    page.window.min_height = 800
    page.window.resizable = True
    page.window.center()
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 10
    page.scroll = None
    page.update()
    
    # 設定檔路徑
    CONFIG_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'yzuCourseBot')
    CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.ini')
    
    # 全域變數
    stop_event = Event()
    
    # ===== UI 元件定義 =====
    
    # 1. 登入資訊區（移至設定分頁）
    account_field = ft.TextField(label="學號 / 帳號", prefix_icon=ft.Icons.PERSON)
    password_field = ft.TextField(label="密碼", password=True, can_reveal_password=True, prefix_icon=ft.Icons.LOCK)
    remember_checkbox = ft.Checkbox(label="記住我的帳號密碼", value=False)
    
    login_card = ft.Card(
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Text("登入資訊", size=14, weight=ft.FontWeight.BOLD),
                    ft.Text("更新帳號資料並選擇是否保存於本機設定檔。", size=12, color=ft.Colors.GREY_600),
                    account_field,
                    password_field,
                    remember_checkbox,
                    ft.Row(
                        [
                            ft.ElevatedButton("儲存設定", icon=ft.Icons.SAVE, on_click=lambda e: save_config()),
                            ft.OutlinedButton(
                                "清除已儲存資料",
                                icon=ft.Icons.DELETE,
                                style=ft.ButtonStyle(color=ft.Colors.RED),
                                on_click=lambda e: clear_config()
                            )
                        ],
                        alignment=ft.MainAxisAlignment.END,
                        spacing=10
                    ),
                    ft.Text(f"設定檔位置: {CONFIG_FILE}", size=11, color=ft.Colors.GREY),
                ],
                spacing=8
            ),
            padding=12
        ),
        expand=True
    )
    
    # 2. 課程清單區
    courses_field = ft.TextField(
        multiline=True,
        min_lines=6,
        max_lines=6,
        hint_text="每行一個，格式：部門代碼,課程代碼（例：312,EEB219A）",
        text_size=13,
        border_radius=8,
        bgcolor=ft.Colors.WHITE,
        border_color=ft.Colors.GREY_400,
    )
    
    courses_card = ft.Container(
        bgcolor=ft.Colors.WHITE,
        border_radius=12,
        border=ft.border.all(1, ft.Colors.GREY_200),
        padding=12,
        content=ft.Column(
            [
                ft.Text("課程清單", size=14, weight=ft.FontWeight.BOLD),
                ft.Text("輸入需搶選的課程，格式：部門代碼,課程代碼", size=12, color=ft.Colors.GREY_600),
                ft.Container(
                    content=courses_field,
                    padding=8,
                    bgcolor=ft.Colors.GREY_50,
                    border_radius=10,
                )
            ],
            spacing=8
        )
    )
    
    # 3. 設定與操作區
    delay_field = ft.TextField(label="延遲 (秒)", value="2.5", width=90, keyboard_type=ft.KeyboardType.NUMBER)
    
    start_btn = ft.ElevatedButton(
        "開始選課",
        icon=ft.Icons.PLAY_ARROW,
        style=ft.ButtonStyle(
            color=ft.Colors.WHITE,
            bgcolor=ft.Colors.GREEN,
            shape=ft.RoundedRectangleBorder(radius=8),
        ),
        height=40,
        width=135
    )
    
    stop_btn = ft.OutlinedButton(
        "停止",
        icon=ft.Icons.STOP,
        style=ft.ButtonStyle(
            color=ft.Colors.RED,
            shape=ft.RoundedRectangleBorder(radius=8),
        ),
        height=40,
        width=100,
        disabled=True
    )
    
    action_row = ft.Row(
        [
            delay_field,
            ft.Container(width=15), # Spacer
            start_btn,
            stop_btn
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
    )
    
    # 4. 課程狀態區（自訂表頭 + 滾動內容）
    status_entries = {}
    
    status_header = ft.Container(
        content=ft.Row(
            [
                ft.Container(ft.Text("課程代碼", size=13, weight=ft.FontWeight.BOLD), width=120),
                ft.Container(ft.Text("狀態", size=13, weight=ft.FontWeight.BOLD), expand=True),
                ft.Container(ft.Text("最後更新", size=13, weight=ft.FontWeight.BOLD), width=100, alignment=ft.alignment.center_right),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=ft.Colors.BLUE_100,
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
    )
    
    status_list = ft.ListView(
        controls=[],
        spacing=0,
        auto_scroll=True,
        padding=0,
        height=180,
    )
    
    status_card = ft.Container(
        bgcolor=ft.Colors.WHITE,
        border_radius=12,
        border=ft.border.all(1, ft.Colors.GREY_200),
        padding=12,
        content=ft.Column(
            [
                ft.Text("選課狀態", size=14, weight=ft.FontWeight.BOLD),
                ft.Text("顯示目前各課程的選課狀態與最後更新時間", size=12, color=ft.Colors.GREY_600),
                ft.Container(
                    border=ft.border.all(1, ft.Colors.GREY_400),
                    border_radius=10,
                    bgcolor=ft.Colors.WHITE,
                    content=ft.Column(
                        [
                            status_header,
                            ft.Divider(height=1, color=ft.Colors.GREY_300, thickness=1),
                            ft.Container(
                                content=status_list,
                                height=180,
                                bgcolor=ft.Colors.WHITE,
                                border_radius=ft.border_radius.only(bottom_left=10, bottom_right=10),
                                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                            )
                        ],
                        spacing=0
                    )
                )
            ],
            spacing=8
        )
    )
    
    # 5. 日誌區
    log_view = ft.ListView(
        height=100, # 預設高度
        spacing=6,
        padding=6,
        auto_scroll=True,
    )
    
    log_container = ft.Container(
        content=log_view,
        border=ft.border.all(1, ft.Colors.GREY_300),
        border_radius=8,
        bgcolor=ft.Colors.GREY_50,
        padding=6,
        height=100 + 14, # 預設高度 + padding
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )
    
    clear_log_btn = ft.TextButton("清空日誌", icon=ft.Icons.DELETE_OUTLINE, on_click=lambda e: clear_log())
    
    log_card = ft.Container(
        bgcolor=ft.Colors.WHITE,
        border_radius=12,
        border=ft.border.all(1, ft.Colors.GREY_200),
        padding=12,
        content=ft.Column(
            [
                ft.Row(
                    [ft.Text("執行日誌", size=14, weight=ft.FontWeight.BOLD), clear_log_btn],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ),
                log_container
            ],
            spacing=8
        )
    )
    
    # 設定頁面內容
    settings_content = ft.Column(
        [
            ft.Text("帳號與登入設定", size=18, weight=ft.FontWeight.BOLD),
            login_card,
            ft.Container(height=15),
            ft.Text("關於", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.Text("版本: 2.0.0", size=13),
            ft.Text("作者: tsz7250", size=13),
            ft.TextButton("GitHub Repository", url="https://github.com/tsz7250/yzuCourseBot")
        ],
        spacing=10,
        scroll=ft.ScrollMode.AUTO
    )

    # ===== 功能函數 =====
    
    def log_message(msg, color=ft.Colors.BLACK):
        log_view.controls.append(ft.Text(msg, color=color, size=13, font_family="Consolas"))
        page.update()
        
    def clear_log():
        log_view.controls.clear()
        page.update()
    
    def show_center_snack(message, bgcolor=ft.Colors.RED, duration=2, icon=None):
        """顯示居中的提示訊息，帶有淡入和淡出動畫"""
        # 根據背景顏色選擇圖標
        if icon is None:
            if bgcolor == ft.Colors.GREEN:
                icon = ft.Icons.CHECK_CIRCLE
            elif bgcolor == ft.Colors.RED:
                icon = ft.Icons.INFO_OUTLINE
            else:
                icon = ft.Icons.INFO_OUTLINE
        
        snack_box = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(icon, color=ft.Colors.WHITE, size=20),
                    ft.Text(message, color=ft.Colors.WHITE, size=13),
                ],
                spacing=8,
                tight=True,
            ),
            bgcolor=bgcolor,
            padding=ft.padding.symmetric(horizontal=20, vertical=12),
            border_radius=8,
            opacity=0.0,  # 初始透明度為0，用於淡入動畫
        )
        
        overlay_container = ft.Container(
            content=ft.Stack(
                controls=[snack_box],
            ),
            left=0,
            top=0,
            right=0,
            bottom=0,
            alignment=ft.alignment.center,
        )
        page.overlay.append(overlay_container)
        page.update()
        
        # 淡入和淡出動畫
        def fade_in_out_and_close():
            # 緩動函數：ease-out (用於淡入)
            def ease_out(t):
                return 1 - (1 - t) ** 3
            
            # 緩動函數：ease-in (用於淡出)
            def ease_in(t):
                return t ** 3
            
            # 淡入動畫（0.2秒，15步，ease-out）
            fade_in_duration = 0.2
            fade_in_steps = 15
            fade_in_step_time = fade_in_duration / fade_in_steps
            
            if overlay_container in page.overlay:
                for i in range(fade_in_steps + 1):
                    t = i / fade_in_steps
                    opacity = ease_out(t)
                    snack_box.opacity = opacity
                    page.update()
                    time.sleep(fade_in_step_time)
            
            # 等待顯示時間（扣除淡入和淡出時間）
            display_time = max(0, duration - fade_in_duration - 0.4)
            if display_time > 0:
                time.sleep(display_time)
            
            # 淡出動畫（0.4秒，20步，ease-in）
            fade_out_duration = 0.4
            fade_out_steps = 20
            fade_out_step_time = fade_out_duration / fade_out_steps
            
            if overlay_container in page.overlay:
                for i in range(fade_out_steps + 1):
                    t = i / fade_out_steps
                    opacity = 1.0 - ease_in(t)  # 從1.0降到0.0
                    snack_box.opacity = opacity
                    page.update()
                    time.sleep(fade_out_step_time)
            
            # 移除overlay
            if overlay_container in page.overlay:
                page.overlay.remove(overlay_container)
                page.update()
        
        Thread(target=fade_in_out_and_close, daemon=True).start()
        
    def update_status(course_key, status):
        # 狀態對應的顏色與圖示
        status_map = {
            "waiting": (ft.Colors.GREY, "等待中", ft.Icons.ACCESS_TIME),
            "trying": (ft.Colors.BLUE, "嘗試中...", ft.Icons.REFRESH),
            "success": (ft.Colors.GREEN, "已選上", ft.Icons.CHECK_CIRCLE),
            "retry": (ft.Colors.ORANGE, "重試中", ft.Icons.REPLAY),
            "error": (ft.Colors.RED, "失敗", ft.Icons.ERROR),
        }
        
        color, text, icon = status_map.get(status, (ft.Colors.BLACK, status, ft.Icons.INFO))
        timestamp = time.strftime("%H:%M:%S")
        
        entry = status_entries.get(course_key)
        if entry:
            entry["icon"].name = icon
            entry["icon"].color = color
            entry["status_text"].value = text
            entry["status_text"].color = color
            entry["time_text"].value = timestamp
        else:
            code_text = ft.Text(course_key, weight=ft.FontWeight.BOLD)
            status_icon = ft.Icon(icon, color=color, size=16)
            status_text = ft.Text(text, color=color)
            time_text = ft.Text(timestamp)
            
            row = ft.Container(
                padding=ft.padding.symmetric(horizontal=12, vertical=10),
                bgcolor=ft.Colors.WHITE,
                border=ft.border.only(bottom=ft.border.BorderSide(1, ft.Colors.GREY_200)),
                content=ft.Row(
                    [
                        ft.Container(code_text, width=120),
                        ft.Container(ft.Row([status_icon, status_text], spacing=5), expand=True),
                        ft.Container(time_text, width=100, alignment=ft.alignment.center_right),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )
            
            status_entries[course_key] = {
                "row": row,
                "icon": status_icon,
                "status_text": status_text,
                "time_text": time_text,
            }
            status_list.controls.append(row)
        page.update()

    def run_bot_thread(account, password, courses_list, delay):
        try:
            # 初始化狀態
            for course in courses_list:
                key = course.split(',')[1] if ',' in course else course
                update_status(key, "waiting")
            
            depts = set([i.split(',')[0] for i in courses_list])
            
            bot = CourseBot(
                account, 
                password, 
                log_callback=lambda msg: log_message(msg),
                status_callback=update_status,
                stop_event=stop_event
            )
            
            if stop_event.is_set(): return

            log_message("正在登入...", ft.Colors.BLUE)
            if not bot.login():
                log_message("登入失敗！", ft.Colors.RED)
                finish_bot()
                return
                
            if stop_event.is_set(): return
            
            log_message("正在獲取課程資料...", ft.Colors.BLUE)
            if not bot.getCourseDB(depts):
                log_message("獲取課程資料失敗！", ft.Colors.RED)
                finish_bot()
                return
                
            if stop_event.is_set(): return
            
            log_message("開始選課...", ft.Colors.GREEN)
            bot.selectCourses(courses_list, delay)
            
            log_message("選課流程結束！", ft.Colors.GREEN)
            
        except Exception as e:
            log_message(f"發生錯誤: {str(e)}", ft.Colors.RED)
        finally:
            finish_bot()

    def start_bot(e):
        # 檢查登入資訊
        account = ""
        password = ""
        
        try:
            if account_field.value:
                account = str(account_field.value).strip()
            if password_field.value:
                password = str(password_field.value).strip()
        except Exception as ex:
            log_message(f"讀取帳號密碼時發生錯誤: {ex}", ft.Colors.RED)
        
        if not account or not password:
            show_center_snack("請先到「設定」分頁輸入帳號或密碼", ft.Colors.RED, duration=2)
            return
            
        if not courses_field.value:
            show_center_snack("請輸入課程清單", ft.Colors.RED, duration=2)
            return
        
        # 重置狀態列表
        status_list.controls.clear()
        status_entries.clear()
        page.update()

        # 鎖定 UI
        start_btn.disabled = True
        stop_btn.disabled = False
        account_field.disabled = True
        password_field.disabled = True
        courses_field.disabled = True
        delay_field.disabled = True
        page.update()
        
        stop_event.clear()
        
        # 解析課程
        courses_list = [line.strip() for line in courses_field.value.split('\n') if line.strip()]
        delay = float(delay_field.value)
        
        # 啟動執行緒
        t = Thread(target=run_bot_thread, args=(account_field.value, password_field.value, courses_list, delay), daemon=True)
        t.start()

    def stop_bot_click(e):
        stop_event.set()
        log_message("正在停止...", ft.Colors.ORANGE)
        stop_btn.disabled = True
        page.update()

    def finish_bot():
        start_btn.disabled = False
        stop_btn.disabled = True
        account_field.disabled = False
        password_field.disabled = False
        courses_field.disabled = False
        delay_field.disabled = False
        page.update()

    def load_config():
        if os.path.exists(CONFIG_FILE):
            try:
                config = configparser.ConfigParser()
                config.read(CONFIG_FILE, encoding='utf-8')
                if 'Default' in config:
                    account_field.value = config['Default'].get('Account', '')
                    password_field.value = config['Default'].get('Password', '')
                    remember = config['Default'].getboolean('RememberMe', False)
                    remember_checkbox.value = remember
                    if remember:
                        log_message("已載入儲存的帳號資訊", ft.Colors.BLUE)
            except Exception:
                pass
        page.update()

    def save_config():
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            config = configparser.ConfigParser()
            config['Default'] = {
                'Account': account_field.value,
                'Password': password_field.value,
                'RememberMe': str(remember_checkbox.value)
            }
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                config.write(f)
            show_center_snack("設定已儲存", ft.Colors.GREEN, duration=2)
        except Exception as e:
            show_center_snack(f"儲存失敗: {e}", ft.Colors.RED, duration=2)

    def clear_config():
        if os.path.exists(CONFIG_FILE):
            os.remove(CONFIG_FILE)
            show_center_snack("已清除設定", ft.Colors.GREEN, duration=2)
        remember_checkbox.value = False
        account_field.value = ""
        password_field.value = ""
        page.update()

    # 綁定事件
    start_btn.on_click = start_bot
    stop_btn.on_click = stop_bot_click

    # 建立分頁
    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            ft.Tab(
                text="選課",
                icon=ft.Icons.DASHBOARD,
                content=ft.Container(
                    content=ft.Column(
                        [
                            courses_card,
                            ft.Container(content=action_row, padding=ft.padding.symmetric(vertical=5)),
                            status_card,
                            log_card
                        ],
                        spacing=10,
                        scroll=ft.ScrollMode.AUTO
                    ),
                    padding=ft.padding.only(top=15, left=0, right=0, bottom=0),
                    expand=True
                ),
            ),
            ft.Tab(
                text="設定",
                icon=ft.Icons.SETTINGS,
                content=ft.Container(content=settings_content, padding=15),
            ),
        ],
        expand=True,
    )

    page.add(tabs)
    load_config()

    # 動態高度自適應：監聽視窗調整大小事件
    def page_resize(e):
        # 扣除上方固定元件、標籤列與 Padding 等約 630px
        available_height = page.height - 630
        
        # 設定最小高度為 100px
        new_height = max(100, available_height)
        
        # 只有在高度需要改變時才更新，避免過度渲染
        if log_view.height != new_height:
            log_view.height = new_height
            log_container.height = new_height + 14
            page.update()

    page.on_resize = page_resize
    # 初始化高度
    page_resize(None)

if __name__ == "__main__":
    # 需要 freeze_support() 以支援 PyInstaller 打包後 multiprocessing
    freeze_support()
    # 使用自定義視窗模式運行 Flet
    ft.app(target=main)
