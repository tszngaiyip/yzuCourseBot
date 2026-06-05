import sys
import os
import threading
import time

# 將上層目錄加入 sys.path，以便載入 bot_core
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from bot_core import CourseBot

# 如果 oscpy 無法載入，這會導致 Service 掛掉，請確認 Buildozer spec 已加入 oscpy
try:
    from oscpy.server import OSCThreadServer
    from oscpy.client import OSCClient
except ImportError:
    print("oscpy is not installed. Service cannot start.")
    sys.exit(1)

try:
    from plyer import notification
except ImportError:
    notification = None


# Service 監聽 3000, App 監聽 3001
SERVICE_PORT = 3000
APP_PORT = 3001

osc_client = OSCClient('127.0.0.1', APP_PORT)

bot_instance = None
bot_thread = None

def notify_event(title, message):
    if notification:
        try:
            notification.notify(title=title, message=message, app_name="YZUCourseBot")
        except Exception as e:
            print("Notification failed:", e)

def send_log(msg):
    try:
        osc_client.send_message(b'/log', [msg.encode('utf-8')])
    except Exception as e:
        print("Failed to send log via OSC:", e)

def send_status(key, status):
    try:
        osc_client.send_message(b'/status', [key.encode('utf-8'), status.encode('utf-8')])
    except Exception as e:
        print("Failed to send status via OSC:", e)
        
    if status == "success":
        notify_event("選課成功", f"{key} 已經成功選上！")

def bot_task(account, password, courses_str, delay):
    global bot_instance
    try:
        bot_instance = CourseBot(
            account, password,
            log_callback=send_log,
            status_callback=send_status
        )
        lines = [line.strip() for line in courses_str.split('\n') if line.strip()]
        if not lines:
            send_log("[color=#F44336]沒有輸入有效的課程代碼[/color]")
            notify_event("執行停止", "沒有輸入有效的課程代碼")
            return
            
        coursesList = lines
        
        for course in coursesList:
            key = course.split(',')[1] if ',' in course else course
            send_status(key, "waiting")
        
        depts = set([i.split(',')[0] for i in coursesList if ',' in i])
        if not depts:
            send_log("[color=#F44336]課程代碼格式錯誤。[/color]")
            notify_event("執行停止", "課程代碼格式錯誤")
            return

        send_log("[color=#2196F3]正在登入...[/color]")
        if bot_instance.login():
            send_log("[color=#2196F3]正在獲取課程資料...[/color]")
            if bot_instance.getCourseDB(depts):
                send_log("[color=#4CAF50]開始選課...[/color]")
                bot_instance.selectCourses(coursesList, delay)
                send_log("[color=#4CAF50]選課流程結束！[/color]")
                notify_event("選課完成", "所有指定課程皆已處理完畢！")
            else:
                send_log("[color=#F44336]獲取課程資料失敗！[/color]")
                notify_event("執行異常", "獲取課程資料失敗")
        else:
            send_log("[color=#F44336]登入失敗！[/color]")
            notify_event("登入失敗", "帳號密碼錯誤或無法登入")
    except Exception as e:
        send_log(f"[color=#F44336]發生未預期錯誤: {e}[/color]")
        notify_event("執行發生錯誤", f"未預期錯誤: {e}")
    finally:
        send_log("[color=#FF9800]Bot 已經完全停止執行。[/color]")
        try:
            for _ in range(3):
                osc_client.send_message(b'/done', [])
                time.sleep(0.2)
        except:
            pass

def on_start(account_b, password_b, courses_b, delay_f):
    global bot_thread, bot_instance
    account = account_b.decode('utf-8')
    password = password_b.decode('utf-8')
    courses = courses_b.decode('utf-8')
    delay = float(delay_f)
    
    if bot_instance and bot_instance.running:
        send_log("Bot 已經在執行中！")
        return

    bot_thread = threading.Thread(target=bot_task, args=(account, password, courses, delay))
    bot_thread.daemon = True
    bot_thread.start()

def on_stop(*args):
    global bot_instance
    send_log("[color=#FF9800]正在停止...[/color]")
    if bot_instance and bot_instance.running:
        bot_instance.running = False
    else:
        try:
            for _ in range(3):
                osc_client.send_message(b'/done', [])
                time.sleep(0.2)
        except:
            pass

def ping(*args):
    try:
        osc_client.send_message(b'/pong', [])
    except:
        pass

if __name__ == '__main__':
    osc_server = OSCThreadServer()
    osc_server.listen('127.0.0.1', SERVICE_PORT, default=True)
    osc_server.bind(b'/start', on_start)
    osc_server.bind(b'/stop', on_stop)
    osc_server.bind(b'/ping', ping)
    
    # 保持 Service 執行
    while True:
        time.sleep(1)
