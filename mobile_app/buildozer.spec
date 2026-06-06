[app]
title = YZUCourseBot
package.name = yzucoursebot
package.domain = org.yzu

# 原始碼目錄 (包含 main.py)
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,npz,otf,ttf

version = 2.0.3

# 應用程式圖示與載入畫面
icon.filename = %(source.dir)s/../pic/icon.png
presplash.filename = %(source.dir)s/../pic/presplash.png
android.presplash_color = #2D88FF

# 應用程式所需的 Python 套件
requirements = python3,kivy,https://github.com/kivymd/KivyMD/archive/master.zip,materialyoucolor,asyncgui,asynckivy,materialshapes,requests,beautifulsoup4,numpy,pillow,typing-extensions,soupsieve,oscpy,plyer
p4a.branch = v2024.01.21
android.minapi = 24
android.accept_sdk_license = True

# 服務
services = BotService:service/main.py:foreground

# 手機方向
orientation = portrait

# 權限
android.permissions = INTERNET,FOREGROUND_SERVICE,WAKE_LOCK,POST_NOTIFICATIONS

# 解決長螢幕比例產生黑邊的問題
android.meta_data = android.max_aspect=2.5

# 桌面作業系統相關設定 (GitHub Actions 通常是 Linux，此處 osx 選項為備用)
osx.python_version = 3
osx.kivy_version = 2.2.0

[buildozer]
# 控制輸出訊息層級
log_level = 2
warn_on_root = 1
