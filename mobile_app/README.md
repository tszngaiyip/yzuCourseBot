# yzuCourseBot 手機版 (Android)

這是一個基於 Kivy 框架開發的元智選課機器人手機版 (Android) 應用程式。您可以透過手機直接使用選課功能，享受更便利的跨平台體驗。

## 系統需求
- **支援系統**: Android 7.0 或以上版本
- **網路需求**: 需要網路連線

## 下載與安裝

### 1. 下載 APK
請至本專案的 [Releases 頁面](https://github.com/tsz7250/yzuCourseBot/releases) 下載最新版本的 `YZUCourseBot-Android.apk`。

### 2. 安裝說明
1. 下載 APK 後，點擊檔案進行安裝。
2. 由於本應用程式尚未上架 Google Play，系統可能會跳出**「安裝未知的應用程式」**或**「Play 護航 (Play Protect)」**的警告。
3. 請選擇 **「允許來自此來源的應用程式」** 或 **「仍要安裝」** 以完成安裝。

## 介面操作說明

1. 開啟應用程式後，您會看到與電腦版類似的登入介面。
2. 依序輸入以下資訊：
   - **帳號** (您的 Portal 學號)
   - **密碼** (您的 Portal 密碼)
   - **課程清單** (每行一個課程，格式為 `系所代碼,課程代碼+班級`)
   - **延遲時間** (選填，預設為 2.5 秒)
3. 點擊 **「開始選課」**，系統將自動於背景執行選課流程。
4. 下方的 **「執行記錄」** 區塊會顯示即時的選課狀態。
5. 若要中斷，請點擊 **「停止」**。

---

## 給開發者：如何自行編譯 APK

若您希望自行修改程式碼並打包為 APK，我們提供了自動化的編譯腳本。打包過程仰賴 [Buildozer](https://github.com/kivy/buildozer)，目前僅支援在 Linux 或 macOS 環境下運行（Windows 使用者可透過 WSL 執行）。

### 驗證碼模型轉換

主專案預設使用 `.onnx` 格式的 CNN 驗證碼辨識模型。為了降低手機端的套件依賴與提升推理效能，手機版改用純 NumPy 陣列格式 (`.npz`) 進行離線推理。

如果您替換了根目錄的 `model.onnx`，請務必重新匯出手機版專用的權重檔：
1. 確保您的 Python 環境已安裝 `onnx` 與 `numpy`。
2. 進入 `mobile_app` 資料夾並執行轉換腳本：
   ```bash
   cd mobile_app
   python export_weights.py
   ```
3. 執行成功後，目錄下將會更新 `model_weights.npz` 檔案。後續打包 APK 時會自動將此檔案納入。

### Windows 環境編譯 (使用 WSL)

1. 請確保您的系統已安裝 [WSL (Windows Subsystem for Linux)](https://learn.microsoft.com/zh-tw/windows/wsl/install)。
2. 在 `mobile_app` 目錄下，雙擊執行 `build_apk.bat`。
3. 腳本會自動啟動 WSL，檢查並安裝相關的編譯依賴（包含 OpenJDK 17、Buildozer 等）。這可能需要您輸入 WSL 的 sudo 密碼。
4. 腳本會使用 rsync 將專案複製到 Linux 的原生檔案系統進行編譯，以避免 NTFS 檔案系統導致的錯誤。
5. 編譯過程可能需要數十分鐘（視電腦效能而定），完成後，產生的 APK 檔案會被自動複製回 Windows 的 `mobile_app/bin/` 目錄中。

### macOS / Linux 環境編譯

請在終端機中手動執行以下指令（需先安裝 Python3 與 Buildozer）：
```bash
# 前往 mobile_app 目錄
cd mobile_app

# 執行 buildozer 進行 debug 版本編譯
buildozer android debug
```
編譯完成後，APK 將會產生在 `bin/` 目錄中。
