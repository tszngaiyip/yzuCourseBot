# yzuCourseBot 元智選課機器人

## 專案說明
本專案是基於原始 yzuCourseBot 進行 fork 並針對 Windows 環境優化的版本。主要修改包括：
- 更新套件相容性，支援 Python 3.12
- 修正 Windows 平台的依賴問題
- 提供完整的 Windows 安裝指南
- 優化在 Windows 環境下的執行穩定性

## Introduction
本專案整合了以下開源專案：
- **選課邏輯**：基於原始 yzuCourseBot 進行 fork
- **驗證碼識別**：使用 [CNN-model-for-YZU-cpatcha-OCR](https://github.com/Doem/CNN-model-for-YZU-cpatcha-OCR) 的 CNN 模型

此 Windows 優化版本針對 Windows 環境進行相容性調整，提供更穩定的執行體驗。

## Remind
請斟酌使用本機器人程式，並自行負責使用後所造成的損失!

## Usage

### 1. 新增 `accounts.ini` 存放Portal帳密的檔案，格式如下:
```
[Default]
Account= your account
Password= your password
```

### 2. 修改 `yzuCourseBot.py` 中的`coursesList`變數新增想選的課程清單，格式如下:
```
coursesList = [
    '304,CS352A', 
    '901,LS239A', 
    '304,CS354A'
]
```

**304**: 為系所編號

**CS352A**: 為課程編號加上班級編號，CS352 + A

以上資訊都能在課程查詢網站或是選課系統中得知的訊息

### 3. 執行 `yzuCourseBot.py`
```
$ python yzuCourseBot.py
```

**請用Python3以上的版本執行**


## Bug Report
請來信 aa0917954358@gmail.com 或是開issue，謝謝!

## Windows 安裝教學
請參考 [INSTALL_WINDOWS.md](INSTALL_WINDOWS.md) 文件以獲得完整的 Windows 安裝指南。
