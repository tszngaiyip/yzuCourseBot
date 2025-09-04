# yzuCourseBot Windows 安裝指南

## 系統需求

- Windows 10 或更高版本
- Python 3.12.0 (建議版本，確保最佳相容性)
- Microsoft Visual C++ Redistributable (必要組件)

## 安裝步驟

### 0. 安裝 Microsoft Visual C++ Redistributable

**重要：這是必要的系統組件，請先安裝！**

請從以下連結下載並安裝 Microsoft Visual C++ Redistributable：

```
https://aka.ms/vs/17/release/vc_redist.x64.exe
```

下載完成後，以管理員身分執行安裝程式。

### 1. 安裝 Python

請從 [Python 官網](https://www.python.org/downloads/release/python-3120/) 下載並安裝 **Python 3.12.0**。

**重要：安裝時請勾選 "Add Python to PATH" 選項！**

### 2. 驗證 Python 安裝

開啟命令提示字元 (cmd) 或 PowerShell，執行：

```cmd
python --version
```

或

```cmd
python3 --version
```

應該顯示 Python 3.12.0 或相近版本。

### 3. 下載專案

下載或克隆此專案到本地目錄，例如：

```cmd
git clone <repository-url>
cd yzuCourseBot-master
```

### 4. 安裝相依套件

在專案目錄中執行：

```cmd
pip install -r requirements.txt
```

如果遇到權限問題，可以使用：

```cmd
pip install --user -r requirements.txt
```

### 5. 配置帳號

首次運行程式時，會自動創建 `accounts.ini` 檔案：

```cmd
python yzuCourseBot.py
```

然後編輯 `accounts.ini` 檔案，填入您的帳號和密碼：

```ini
[Default]
Account=your_student_id
Password=your_password
```

### 6. 設定選課清單

編輯 `yzuCourseBot.py` 檔案中的 `coursesList`，填入您要選的課程：

```python
coursesList = [
    '304,CS250B',  # 格式：'系所代碼,課程代碼'
    # 添加更多課程...
]
```

## 套件說明

此專案使用的主要套件：

- **beautifulsoup4**: HTML 解析
- **lxml**: XML/HTML 解析引擎
- **numpy**: 數值計算
- **opencv-python**: 圖像處理 (驗證碼識別)
- **requests**: HTTP 請求
- **h5py**: 模型檔案讀取
- **tensorflow**: 機器學習 (驗證碼識別模型)
- **configparser**: 配置檔案解析

## 注意事項

1. 請確保您的學校帳號密碼正確
2. 選課系統需要在開放時間內使用
3. 建議在穩定的網路環境下運行
4. 請遵守學校的選課規定和系統使用條款

## 技術支援

如果遇到問題，請：

1. 首先運行 `python test_environment.py` 檢查環境
2. 檢查 Python 和套件版本是否符合要求
3. 查看錯誤訊息並搜尋相關解決方案

---

**免責聲明**：此工具僅供學習和研究目的，使用者需自行承擔使用風險並遵守相關規定。