import os
import time
import requests
import numpy as np
from bs4 import BeautifulSoup
import onnxruntime as ort
from PIL import Image

class CourseBot:
    def __init__(self, account, password, log_callback=None, status_callback=None):
        self.account = account
        self.password = password
        self.coursesDB = {}
        self.log_callback = log_callback
        self.status_callback = status_callback

        # 使用 onnxruntime 讀取 ONNX
        self.net = ort.InferenceSession('model.onnx')
        self.n_classes = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'

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
        self.running = True

    def predict(self, img):
        input_name = self.net.get_inputs()[0].name
        output_names = [o.name for o in self.net.get_outputs()]
        
        # 執行預測
        prediction = self.net.run(output_names, {input_name: np.array([img], dtype=np.float32)})

        predicStr = ""
        for pred in prediction:
            predicStr += self.n_classes[np.argmax(pred[0])]
        return predicStr

    def captchaOCR(self):
        img = Image.open('captcha.png').convert('RGB')
        img_np = np.array(img, dtype=np.float32)
        # BGR format
        img_bgr = img_np[:, :, ::-1]
        captchaImg = img_bgr / 255.0
        return self.predict(captchaImg)

    def login(self):
        while self.running:
            self.session.cookies.clear()
            with self.session.get(self.captchaUrl, stream=True) as captchaHtml:
                with open('captcha.png', 'wb') as img:
                    img.write(captchaHtml.content)
            captcha = self.captchaOCR()

            loginHtml = self.session.get(self.loginUrl)
            
            if '選課系統尚未開放!' in loginHtml.text:
                self.log('選課系統尚未開放! 稍後重試...')
                for _ in range(5):
                    if not self.running: return False
                    time.sleep(1)
                continue

            parser = BeautifulSoup(loginHtml.text, 'html.parser')
            
            try:
                self.loginPayLoad['__VIEWSTATE'] = parser.select("#__VIEWSTATE")[0]['value']
                self.loginPayLoad['__VIEWSTATEGENERATOR'] = parser.select("#__VIEWSTATEGENERATOR")[0]['value']
                self.loginPayLoad['__EVENTVALIDATION'] = parser.select("#__EVENTVALIDATION")[0]['value']
                self.loginPayLoad['DPL_SelCosType'] = parser.select("#DPL_SelCosType option")[1]['value']
            except IndexError:
                self.log("解析登入頁面失敗，可能系統有變動或阻擋")
                return False

            self.loginPayLoad['Txt_CheckCode'] = captcha

            result = self.session.post(self.loginUrl, data=self.loginPayLoad)
            if ("parent.location ='SelCurr.aspx?Culture=zh-tw'" in result.text):
                self.log('Login Successful! {}'.format(captcha))
                return True
            elif ("資料庫發生異常" in result.text):
                self.log('帳號或密碼錯誤，請重新確認。')
                return False
            elif ("您未在此階段選課時程之內!請於時程內選課!!" in result.text):
                self.log('您未在此階段選課時程之內!請於時程內選課!!')
                return False
            else:
                self.log("Login Failed, Re-try! ({})".format(captcha))
                continue
        return False

    def getCourseDB(self, depts):
        for dept in depts:
            if not self.running: return False
            html = self.session.get(self.courseListUrl)
            if "異常登入" in html.text:
                self.log("異常登入，休息10分鐘!")
                for _ in range(60):
                    if not self.running: return False
                    time.sleep(10)
                continue
            parser = BeautifulSoup(html.text, 'html.parser')

            try:
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
            except IndexError:
                self.log(f'解析 {dept} 失敗，無法取得課程列表')
                return False

            html = self.session.post(self.courseListUrl, data=self.selectPayLoad[dept])
            if "Error" in html.text:
                self.log('Wrong coursesList, please check it again!')
                return False
            parser = BeautifulSoup(html.text, 'html.parser')

            courseList = parser.select("#CosListTable input")
            for courseInfo in courseList:
                tokens = courseInfo.attrs['name'].split(',') 
                if len(tokens) >= 3:
                    key = tokens[1] + tokens[2]
                    courseName = '{} {}'.format(key, tokens[-1].split(' ')[1] if len(tokens[-1].split(' ')) > 1 else tokens[-1])
                    self.coursesDB[key] = {
                        'name': courseName,
                        'mUrl': courseInfo.attrs['name']
                    }
            self.log('Get {} Data Completed!'.format(dept))
        return True

    def selectCourses(self, coursesList, delay=2.5):
        while len(coursesList) > 0 and self.running:
            for course in coursesList.copy():
                if not self.running: break
                tokens = course.split(',')
                if len(tokens) < 2: continue
                dept = tokens[0]
                key  = tokens[1]
                
                if self.status_callback:
                    self.status_callback(key, "trying")

                if key not in self.coursesDB:
                    self.log('{} is not a legal classID'.format(key))
                    coursesList.remove(course)
                    if self.status_callback:
                        self.status_callback(key, "error")
                    continue
                
                html = self.session.post(self.courseListUrl, data=self.selectPayLoad[dept])
                parser = BeautifulSoup(html.text, 'html.parser')

                try:
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
                except IndexError:
                    self.log("選課 Payload 建立失敗，可能被登出")
                    self.login()
                    continue

                self.session.post(self.courseListUrl, data=selectPayLoad)
                html = self.session.get(self.courseSelectUrl + self.coursesDB[key]['mUrl'] + ' ,B,')

                parser = BeautifulSoup(html.text, 'html.parser')
                scripts = parser.select("script")
                if scripts and scripts[0].string:
                    alertMsg = scripts[0].string.split(';')[0]
                    msg_text = alertMsg[7:-2] if len(alertMsg) > 9 else alertMsg
                    self.log('{} {}'.format(self.coursesDB[key]['name'], msg_text))

                    if "加選訊息：" in alertMsg or "已選過" in alertMsg:
                        coursesList.remove(course)
                        if self.status_callback:
                            self.status_callback(key, "success")
                    elif "please log on again!" in alertMsg:
                        if not self.login():
                            return
                    else:
                        if self.status_callback:
                            self.status_callback(key, "retry")
                else:
                    self.log(f'無法解析選課結果 ({key})')
                    if self.status_callback:
                        self.status_callback(key, "error")

                for _ in range(int(delay * 10)):
                    if not self.running: break
                    time.sleep(0.1)
        
        if len(coursesList) == 0:
            self.log("所有指定課程皆已處理完畢！")

    def log(self, msg):
        log_msg = time.strftime("[%Y-%m-%d %H:%M:%S] ", time.localtime()) + str(msg)
        if self.log_callback:
            self.log_callback(log_msg)
        else:
            print(log_msg)
