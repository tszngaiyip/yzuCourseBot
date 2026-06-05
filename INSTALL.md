# yzuCourseBot 安裝與使用指南 (Windows / macOS / Android)

本文件提供 yzuCourseBot 在各平台上的手動安裝與執行說明。如果您想直接使用預編譯好的執行檔，請參考 [電腦版說明](GUI/GUI使用說明.md) 或 [手機版說明](mobile_app/README.md)。

---

## 1. 系統需求 (System Requirements)

### **Windows**
- Windows 10 或更高版本
- Python 3.12.0 (建議版本)
- [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) (必要組件，若出現 DLL 錯誤請安裝)

### **macOS**
- macOS 12 或更高版本 (支援 Intel 及 Apple Silicon)
- Python 3.12.0 (建議版本)
- 建議具備基礎終端機 (Terminal) 使用經驗

### **Android**
- Android 7.0 或更高版本
- （僅編譯需求）Windows WSL 或 Linux/macOS 環境

---

## 2. 安裝步驟 (Installation)

### 第一步：安裝 Python 3.12
- **Windows**: 從 [Python 官網](https://www.python.org/downloads/release/python-3120/) 下載安裝，安裝時**務必勾選 "Add Python to PATH"**。
- **macOS**: 
    - 方式 A (推薦): 使用 [Homebrew](https://brew.sh/) 執行 `brew install python@3.12`。
    - 方式 B: 從 [Python 官網](https://www.python.org/downloads/release/python-3120/) 下載 `.pkg` 安裝。

### 第二步：下載專案
下載或克隆此專案到您的電腦：
```bash
git clone https://github.com/tsz7250/yzuCourseBot.git
cd yzuCourseBot
```

### 第三步：安裝相依套件
在專案目錄下執行以下指令：

**Windows:**
```cmd
pip install -r requirements.txt
```

**macOS:**
```bash
pip3 install -r requirements.txt
# 如果您使用的是 Apple Silicon (M1/M2/M3) 且希望加速驗證碼識別：
pip3 install tensorflow-metal
```

---

## 3. 使用方式 (Usage)

### 方式 A：GUI 圖形介面版本 (推薦)
執行以下指令啟動介面：

- **Windows**: `python GUI/yzuCourseBot_GUI.py`
- **macOS**: `python3 GUI/yzuCourseBot_GUI.py`

在介面中輸入帳密與課程清單（格式：`系所代碼,課程代碼+班級`）後點擊「開始選課」。

### 方式 B：手機版 (Android)
- **下載與安裝**：請參考 [手機版(Android)說明](mobile_app/README.md)。
- **自行編譯 APK**：請參考 [開發者編譯指南](mobile_app/README.md#給開發者如何自行編譯-apk)。

### 方式 C：命令列版本 (CLI)

1. **配置帳號**：
   執行一次 `python yzuCourseBot.py` (Windows) 或 `python3 yzuCourseBot.py` (macOS) 來生成 `accounts.ini`，然後填入帳密。
   ```ini
   [Default]
   Account=您的學號
   Password=您的密碼
   ```

2. **設定課程**：
   編輯 `yzuCourseBot.py` 中的 `coursesList` 變數：
   ```python
   coursesList = [
    '304,CS250B', # 格式：'系所代碼,課程代碼+班級'
    '901,LS239A'
    ]
   ```

   **格式說明：**
  - `304`: 系所編號
  - `CS250B`: 課程編號 + 班級編號（CS250 + B）

3. **執行**：
   - **Windows**: `python yzuCourseBot.py`
   - **macOS**: `python3 yzuCourseBot.py`

---

## 4. 注意事項

1. 請確保您的學校帳號密碼正確
2. 選課系統需要在開放時間內使用
3. 建議在穩定的網路環境下運行
4. 請遵守學校的選課規定和系統使用條款

---

## 5. 常見問題 (FAQ)

**Q: 執行時出現「找不到命令」？**
- **Windows**: 請確認安裝 Python 時有勾選 "Add Python to PATH"，或改用 `py` 命令。
- **macOS**: 請確認使用 `python3` 與 `pip3` 而非舊版的 `python`。

**Q: macOS 出現「無法驗證開發者」或安全性警告？**
- 如果是自行打包的 `.app`，請執行：
  `xattr -rd com.apple.quarantine 元智選課機器人.app`

**Q: Windows 出現 DLL 缺失錯誤？**
- 請重新安裝 [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)。

**Q: Android 安裝 APK 時出現「未知的應用程式」警告？**
- 由於此 APP 尚未上架 Google Play，請在安裝時選擇「允許來自此來源的應用程式」，或在 Play 護航 (Play Protect) 警告中選擇「仍要安裝」。

---

**免責聲明**：此工具僅供學習和研究目的，使用者需自行承擔使用風險並遵守相關規定。
