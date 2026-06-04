import os
import time
import requests
import numpy as np
from bs4 import BeautifulSoup
from PIL import Image
import io
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class TimeoutSession(requests.Session):
    def request(self, *args, **kwargs):
        kwargs.setdefault('timeout', 10)
        return super().request(*args, **kwargs)

class CourseBot:
    @staticmethod
    def conv2d(x, w, b, pads=None, strides=(1,1)):
        x = np.ascontiguousarray(x)
        N, C, H, W = x.shape
        OC, IC, KH, KW = w.shape
        sh, sw = strides
        
        if pads and any(p > 0 for p in pads):
            pt, pl, pb, pr = pads
            x = np.pad(x, ((0,0),(0,0),(pt,pb),(pl,pr)), mode='constant')
            _, _, H, W = x.shape
            
        OH = (H - KH) // sh + 1
        OW = (W - KW) // sw + 1
        
        from numpy.lib.stride_tricks import as_strided
        shape = (N, C, OH, OW, KH, KW)
        strides_shape = (x.strides[0], x.strides[1], x.strides[2]*sh, x.strides[3]*sw, x.strides[2], x.strides[3])
        
        patches = as_strided(x, shape=shape, strides=strides_shape)
        patches_flat = patches.transpose(0, 2, 3, 1, 4, 5).reshape(N * OH * OW, C * KH * KW)
        w_flat = w.reshape(OC, IC * KH * KW)
        
        out = patches_flat @ w_flat.T + b
        out = out.reshape(N, OH, OW, OC).transpose(0, 3, 1, 2)
        return out

    @staticmethod
    def maxpool2d(x, kernel_shape=(2,2), strides=(2,2)):
        x = np.ascontiguousarray(x)
        N, C, H, W = x.shape
        kh, kw = kernel_shape
        sh, sw = strides
        OH = (H - kh) // sh + 1
        OW = (W - kw) // sw + 1
        
        from numpy.lib.stride_tricks import as_strided
        shape = (N, C, OH, OW, kh, kw)
        strides_shape = (x.strides[0], x.strides[1], x.strides[2]*sh, x.strides[3]*sw, x.strides[2], x.strides[3])
        
        patches = as_strided(x, shape=shape, strides=strides_shape)
        return np.max(patches, axis=(4, 5))

    @staticmethod
    def softmax(x, axis=-1):
        e = np.exp(x - np.max(x, axis=axis, keepdims=True))
        return e / np.sum(e, axis=axis, keepdims=True)

    def __init__(self, account, password, log_callback=None, status_callback=None):
        self.account = account
        self.password = password
        self.coursesDB = {}
        self.log_callback = log_callback
        self.status_callback = status_callback

        # 載入 NumPy 權重檔
        weights_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'model_weights.npz')
        self.weights = np.load(weights_path)
        self.n_classes = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'

        self.session = TimeoutSession()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
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
        # Input shape: (20, 60, 3)
        x = np.expand_dims(img, 0) # (1, 20, 60, 3)
        
        # Transpose NHWC -> NCHW
        x = np.transpose(x, (0, 3, 1, 2))  # (1, 3, 20, 60)
        
        # Conv block 1
        x = self.conv2d(x, self.weights['model_1_1/conv2d_1_1/convolution/ReadVariableOp:0'],
                        self.weights['model_1_1/conv2d_1_1/Squeeze:0'], pads=[1,1,1,1])
        x = np.maximum(x, 0)  # ReLU
        
        x = self.conv2d(x, self.weights['model_1_1/conv2d_2_1/convolution/ReadVariableOp:0'],
                        self.weights['model_1_1/conv2d_2_1/Squeeze:0'])
        x = np.maximum(x, 0)  # ReLU
        
        # BN1
        x = x * self.weights['model_1_1/batch_normalization_1_1/batchnorm/mul:0'] + self.weights['const_fold_opt__89']
        
        # MaxPool1
        x = self.maxpool2d(x)
        
        # Conv block 2
        x = self.conv2d(x, self.weights['model_1_1/conv2d_3_1/convolution/ReadVariableOp:0'],
                        self.weights['model_1_1/conv2d_3_1/Squeeze:0'], pads=[1,1,1,1])
        x = np.maximum(x, 0)
        
        x = self.conv2d(x, self.weights['model_1_1/conv2d_4_1/convolution/ReadVariableOp:0'],
                        self.weights['model_1_1/conv2d_4_1/Squeeze:0'])
        x = np.maximum(x, 0)
        
        # BN2
        x = x * self.weights['model_1_1/batch_normalization_2_1/batchnorm/mul:0'] + self.weights['const_fold_opt__87']
        
        # MaxPool2
        x = self.maxpool2d(x)
        
        # Conv block 3
        x = self.conv2d(x, self.weights['model_1_1/conv2d_5_1/convolution/ReadVariableOp:0'],
                        self.weights['model_1_1/conv2d_5_1/Squeeze:0'], pads=[1,1,1,1])
        x = np.maximum(x, 0)
        
        x = self.conv2d(x, self.weights['model_1_1/conv2d_6_1/convolution/ReadVariableOp:0'],
                        self.weights['model_1_1/conv2d_6_1/Squeeze:0'])
        x = np.maximum(x, 0)
        
        # BN3
        x = x * self.weights['model_1_1/batch_normalization_3_1/batchnorm/mul:0'] + self.weights['const_fold_opt__86']
        
        # Transpose back NCHW -> NHWC, then flatten
        x = np.transpose(x, (0, 2, 3, 1))
        flat = x.reshape(x.shape[0], -1)
        
        # 4 digit heads
        result = ''
        for digit_name in ['digit1', 'digit2', 'digit3', 'digit4']:
            w_name = f'model_1_1/{digit_name}_1/Cast/ReadVariableOp:0'
            b_name = f'model_1_1/{digit_name}_1/BiasAdd/ReadVariableOp:0'
            logits = flat @ self.weights[w_name] + self.weights[b_name]
            probs = self.softmax(logits)
            result += self.n_classes[np.argmax(probs[0])]
            
        return result

    def captchaOCR(self, img_data):
        img = Image.open(io.BytesIO(img_data)).convert('RGB')
        img_np = np.array(img, dtype=np.float32)
        # BGR format
        img_bgr = img_np[:, :, ::-1]
        captchaImg = img_bgr / 255.0
        return self.predict(captchaImg)

    def login(self):
        while self.running:
            try:
                self.session.cookies.clear()
                
                # Step 1: 取得驗證碼 (必須先取得，讓伺服器建立 Session，與 GUI 版本一致)
                captchaHtml = self.session.get(self.captchaUrl)
                captcha = self.captchaOCR(captchaHtml.content)
    
                # Step 2: 取得登入頁面與 ViewState 等隱藏欄位
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
                    
                # 嘗試擷取伺服器回傳的 JS alert 訊息
                import re
                alert_msg = None
                alert_match = re.search(br"alert\(['\"](.*?)['\"]\)", result.content)
                if alert_match:
                    try:
                        alert_msg = alert_match.group(1).decode('utf-8')
                    except Exception:
                        alert_msg = alert_match.group(1).decode('big5', errors='ignore')
    
                if alert_msg:
                    self.log('伺服器回應: {} (驗證碼: {})'.format(alert_msg, captcha))
                    if "驗證碼錯誤" in alert_msg:
                        continue  # 只有驗證碼錯誤時才重新嘗試
                    elif "帳號或密碼錯誤" in alert_msg:
                        return False  # 密碼錯誤，直接停止
                    elif "選課時程之內" in alert_msg:
                        return False  # 非選課時間，直接停止
                    else:
                        return False  # 未知錯誤，避免無限迴圈
                else:
                    # 備用檢查 (舊版伺服器訊息)
                    if ("資料庫發生異常" in result.text):
                        self.log('帳號或密碼錯誤，請重新確認。')
                        return False
                    elif ("您未在此階段選課時程之內!請於時程內選課!!" in result.text):
                        self.log('您未在此階段選課時程之內!請於時程內選課!!')
                        return False
                    
                    self.log("Login Failed, 未知錯誤! ({})".format(captcha))
                    continue
            except requests.exceptions.RequestException as e:
                self.log("網路連線異常，重試中...")
                time.sleep(2)
                continue
        return False

    def getCourseDB(self, depts):
        for dept in depts:
            if not self.running: return False
            try:
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
            except requests.exceptions.RequestException as e:
                self.log(f'取得課程清單失敗(網路連線異常): {dept}')
                return False
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
                
                try:
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

                except requests.exceptions.RequestException as e:
                    self.log(f'網路連線異常，稍後重試 ({key})')
                    if self.status_callback:
                        self.status_callback(key, "retry")
                    continue

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
