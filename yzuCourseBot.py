# cmd line version

import os
import cv2
import time
import requests
import numpy as np
import configparser
from bs4 import BeautifulSoup
import onnxruntime as ort

class CourseBot:
    def __init__(self, account, password):
        self.account = account
        self.password = password
        self.coursesDB = {}

        # for ONNX
        self.model = ort.InferenceSession('model.onnx')
        
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

    def predict(self, img):
        input_name = self.model.get_inputs()[0].name
        output_names = [o.name for o in self.model.get_outputs()]
        
        # 執行預測
        prediction = self.model.run(output_names, {input_name: np.array([img], dtype=np.float32)})

        predicStr = ""
        for pred in prediction:
            predicStr += self.n_classes[np.argmax(pred[0])]
        return predicStr

    def captchaOCR(self):
        captchaImg = cv2.imread('captcha.png') / 255.0
        return self.predict(captchaImg)

    # login into system and get session
    def login(self):
        
        while True:
            # clear Session object
            self.session.cookies.clear()

            # download and recognize captch
            with self.session.get(self.captchaUrl, stream= True) as captchaHtml:
                with open('captcha.png', 'wb') as img:
                    img.write(captchaHtml.content)
            captcha = self.captchaOCR()

            # get login data
            loginHtml = self.session.get(self.loginUrl)
            
            # check if system is open
            if '選課系統尚未開放!' in loginHtml.text:
                self.log('選課系統尚未開放!')
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
                continue
            exit(0)

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
                exit(0)
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



    def selectCourses(self, coursesGroups, delay = 0):
        # coursesGroups: list[list[str]]
        active_groups = [g.copy() for g in coursesGroups if len(g) > 0]
        
        while len(active_groups) > 0:
            for group in active_groups.copy():
                group_resolved = False
                successful_course = None
                
                for course in group.copy():
                    tokens = course.split(',')
                    dept = tokens[0]
                    key  = tokens[1]
                    
                    # check if the classID is legal
                    if key not in self.coursesDB:
                        self.log('{} is not a legal classID'.format(key))
                        group.remove(course)
                        if len(group) == 0:
                            if group in active_groups:
                                active_groups.remove(group)
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
                        group_resolved = True
                        successful_course = course
                        break
                    elif "please log on again!" in alertMsg:
                        self.login()

                    time.sleep(delay)

                if group_resolved:
                    self.log('Group completed. Selected: {}'.format(successful_course))
                    for course in group:
                        if course != successful_course:
                            self.log('Skipped course in same group: {}'.format(course))
                    if group in active_groups:
                        active_groups.remove(group)

    def log(self, msg):
        print(time.strftime("[%Y-%m-%d %H:%M:%S]", time.localtime()), msg)

def parse_cmd_courses(courses_list):
    """
    將 flat list 中含有 '---' 的部分切分為多個群組，或支援巢狀 list。
    回傳格式：list[list[str]]
    """
    has_separator = any(isinstance(c, str) and c.strip() == '---' for c in courses_list)
    has_nested_list = any(isinstance(c, list) for c in courses_list)
    
    if not has_separator and not has_nested_list:
        return [[c] for c in courses_list if isinstance(c, str) and c.strip()]
        
    groups = []
    current_group = []
    
    for item in courses_list:
        if isinstance(item, list):
            if current_group:
                groups.append(current_group)
                current_group = []
            groups.append([c.strip() for c in item if isinstance(c, str) and c.strip()])
        elif isinstance(item, str):
            val = item.strip()
            if not val:
                continue
            if val == '---':
                if current_group:
                    groups.append(current_group)
                    current_group = []
            else:
                current_group.append(val)
                
    if current_group:
        groups.append(current_group)
        
    return [g for g in groups if g]

if __name__ == '__main__':
    configFilename = 'accounts.ini'
    if not os.path.isfile(configFilename):
        with open(configFilename, 'a') as f:
            f.writelines(["[Default]\n", "Account= your account\n", "Password= your password"])
            print('input your username and password in accounts.ini')
            exit()
    # get account info fomr ini config file
    config = configparser.ConfigParser()
    config.read(configFilename)
    Account = config['Default']['Account']
    Password = config['Default']['Password']

# the courses you want to select, format: '`deptId`,`courseId``classId`'
# 支援使用 '---' 來分隔不同時段的選課群組（同一群組內擇一選上即跳過其餘）
    coursesList = [
         '304,CS352A'
    ]

    # Time Parameter, sleep n seconds
    delay = 2.5
    
    coursesGroups = parse_cmd_courses(coursesList)
    flat_courses = [c for g in coursesGroups for c in g]
    depts = set([i.split(',')[0] for i in flat_courses])
    
    myBot = CourseBot(Account, Password)
    myBot.login()
    myBot.getCourseDB(depts)
    myBot.selectCourses(coursesGroups, delay)

