[app]
title = YZUCourseBot
package.name = yzucoursebot
package.domain = org.yzu

# 原始碼目錄 (包含 main.py)
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,onnx

version = 1.0

# 應用程式所需的 Python 套件
requirements = python3,kivy,kivymd,requests,beautifulsoup4,numpy,opencv
p4a.branch = v2024.01.21
android.minapi = 24
android.accept_sdk_license = True

# 手機方向
orientation = portrait

# 權限
android.permissions = INTERNET

# 桌面作業系統相關設定 (GitHub Actions 通常是 Linux，此處 osx 選項為備用)
osx.python_version = 3
osx.kivy_version = 2.2.0

[buildozer]
# 控制輸出訊息層級
log_level = 2
warn_on_root = 1
