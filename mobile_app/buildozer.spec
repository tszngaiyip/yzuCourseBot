[app]
title = YZUCourseBot
package.name = yzucoursebot
package.domain = org.yzu

# 原始碼目錄 (包含 main.py)
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,npz,otf,ttf

version = 1.0

# 應用程式所需的 Python 套件
requirements = python3,kivy,https://github.com/kivymd/KivyMD/archive/master.zip,materialyoucolor,asyncgui,asynckivy,materialshapes,requests,beautifulsoup4,numpy,pillow,typing-extensions,soupsieve,oscpy
p4a.branch = v2024.01.21
android.minapi = 24
android.accept_sdk_license = True

# 服務
services = BotService:service/main.py:foreground

# 手機方向
orientation = portrait

# 權限
android.permissions = INTERNET,FOREGROUND_SERVICE,WAKE_LOCK,POST_NOTIFICATIONS

# 桌面作業系統相關設定 (GitHub Actions 通常是 Linux，此處 osx 選項為備用)
osx.python_version = 3
osx.kivy_version = 2.2.0

[buildozer]
# 控制輸出訊息層級
log_level = 2
warn_on_root = 1
