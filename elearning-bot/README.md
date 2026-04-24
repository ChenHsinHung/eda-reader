# elearning-bot

自動化學習機器人，用於完成 elearning.taipei 線上課程。系統會自動登入、播放視頻、作答測驗，並結算學習時數。

## 功能特點

- 🔐 **安全加密**: 帳密本地加密存儲，無需擔心洩露
- 🤖 **全自動化**: 無需人工干預，後台運行
- 📊 **智能辨識**: 動態提取課程完成條件
- 🎯 **精準完成**: 根據條件自動播放視頻至指定進度
- 📝 **自動測驗**: 支持選擇題自動作答
- 📈 **詳細日誌**: 完整記錄所有操作和結果
- 🖥️ **後台運行**: 無頭模式，不影響其他工作- 🌐 **Web 界面**: 提供美觀的網頁控制面板
- 📊 **實時監控**: WebSocket 實時進度和日誌更新
- 🎮 **一鍵操作**: 簡單的開始/停止控制
## 系統要求

- **作業系統**: Windows 10/11 (64-bit)
- **Python**: 3.9 或以上
- **記憶體**: 至少 4GB RAM
- **網路**: 穩定網路連線

## 安裝步驟

### 1. 安裝 Python
從 [python.org](https://www.python.org/downloads/) 下載並安裝 Python 3.9+ (64-bit)
- ✅ 勾選 "Add Python to PATH"
- 驗證安裝: 開啟命令提示字元，執行 `python --version`

### 2. 安裝 Tesseract OCR
從 [GitHub](https://github.com/UB-Mannheim/tesseract/wiki) 下載並安裝 Tesseract-OCR
- 選擇 `tesseract-ocr-w64-setup-v5.x.exe`
- 安裝到預設位置: `C:\Program Files\Tesseract-OCR`
- 驗證安裝: 開啟命令提示字元，執行 `tesseract --version`

### 3. 安裝依賴包
```bash
cd /path/to/elearning-bot
pip install -r requirements.txt
```

### 4. 首次設定
```bash
python setup.py
```
- 系統會提示輸入身分證字號和密碼
- 帳密會被加密並存儲在 `%LOCALAPPDATA%\elearning-bot\`

## 使用方法

### 命令行模式
```bash
# 處理所有可用課程
python main.py

# 處理特定課程
python main.py --courses "課程名稱1" "課程名稱2"

# 限制處理課程數量
python main.py --max-courses 5

# 預覽模式（只顯示會處理哪些課程，不實際執行）
python main.py --dry-run
```

### Web 界面模式 (推薦)
```bash
# 啟動 Web 界面
python main.py --web

# 自訂主機和端口
python main.py --web --web-host 0.0.0.0 --web-port 3000
```

啟動後，在瀏覽器中開啟顯示的 URL (預設: http://127.0.0.1:8080)

#### Web 界面功能：
- 🖥️ **圖形化控制面板**: 直觀的課程選擇和控制按鈕
- 📊 **實時進度顯示**: 課程處理進度和完成統計
- 📝 **即時日誌查看**: 滾動式日誌顯示所有操作
- 🎯 **課程狀態指示**: 顯示課程完成狀態和時數
- ⚡ **一鍵操作**: 簡單的開始/停止控制
- 💾 **日誌導出**: 支援日誌檔案下載

### 進階選項
```bash
# 處理特定類型的課程並限制數量
python main.py --courses "公務類" --max-courses 3

# 組合使用
python main.py --courses "衛生醫療" "資訊科技" --max-courses 10
```

## 設定說明

編輯 `config.py` 來自訂行為：

```python
# 課程選擇
COURSES_TO_COMPLETE = []  # 空列表 = 所有課程

# 測驗設定
AUTO_ANSWER_QUIZ = True          # 是否自動作答測驗
QUIZ_METHOD = "traditional"      # "traditional" 或 "ai"
MIN_QUIZ_SCORE = 60              # 及格分數

# 視頻設定
VIDEO_COMPLETION_THRESHOLD = 0.9 # 視頻完成閾值 (90%)
PLAYBACK_SPEED = 1.0             # 播放速度

# Web 界面設定
ENABLE_WEB_UI = True             # 啟用 Web 界面
WEB_HOST = "127.0.0.1"          # Web 服務器主機
WEB_PORT = 8080                 # Web 服務器端口

# 系統設定
ENABLE_HEADLESS = True           # 後台運行
LOG_LEVEL = "INFO"               # 日誌等級
```

## 檔案結構

```
elearning-bot/
├── main.py              # 主程序
├── auth.py              # 登入模塊
├── course.py            # 課程導航
├── conditions.py        # 條件提取
├── video.py             # 視頻播放
├── quiz.py              # 測驗作答
├── encryption.py        # 加密管理
├── setup.py             # 首次設定
├── config.py            # 設定檔案
├── utils.py             # 工具函數
├── web_ui.py            # Web 界面
├── web_ui_launcher.py   # Web 界面啟動器
├── demo.py              # 演示腳本
├── requirements.txt     # 依賴清單
├── README.md           # 使用說明
├── templates/          # HTML 模板
│   └── index.html
└── static/             # 靜態文件
    ├── css/
    │   └── style.css
    └── js/
        └── app.js
```

加密檔案存儲位置：
```
%LOCALAPPDATA%\elearning-bot\
├── key.bin              # 加密金鑰
├── credentials.enc      # 加密帳密
└── logs/                # 執行日誌
```

## 日誌和監控

### 日誌檔案
- 位置: `%LOCALAPPDATA%\elearning-bot\logs\`
- 命名: `elearning_YYYY-MM-DD.log`
- 輪替: 每個檔案最大 10MB，保留 5 個備份

### 日誌等級
```
DEBUG    - 詳細調試信息
INFO     - 一般操作信息
WARNING  - 警告信息
ERROR    - 錯誤信息
CRITICAL - 嚴重錯誤
```

### 報告檔案
每次執行完成後會生成 JSON 格式的報告：
- 位置: `%LOCALAPPDATA%\elearning-bot\logs\report_[timestamp].json`
- 包含: 完成統計、課程詳情、錯誤信息等

## 故障排除

### 常見問題

**Q: 登入失敗**
- 檢查網路連線
- 確認帳密正確
- 檢查驗證碼識別是否正常

**Q: 視頻無法播放**
- 檢查瀏覽器版本
- 確認網路穩定
- 查看日誌中的詳細錯誤

**Q: 測驗作答失敗**
- 檢查測驗題型是否支援
- 確認頁面結構是否變更
- 考慮手動完成複雜測驗

**Q: 程式無回應**
- 檢查系統資源使用
- 查看日誌檔案
- 嘗試重新啟動

### 重新設定
```bash
# 重設帳密
python setup.py --reset

# 清除所有設定和日誌
# 手動刪除 %LOCALAPPDATA%\elearning-bot\ 目錄
```

## 技術細節

### 安全機制
- Fernet 對稱加密存儲帳密
- 加密金鑰與資料分離存儲
- 記憶體中的敏感資料及時清理
- 日誌中不記錄明文帳密

### 自動化策略
- Selenium WebDriver 模擬瀏覽器操作
- Tesseract OCR 識別驗證碼
- 正則表達式和 DOM 解析提取條件
- 試錯法和關鍵詞匹配作答測驗

### 錯誤處理
- 指數級退避重試機制
- 異常捕獲和詳細日誌記錄
- 單課程失敗不影響其他課程
- 超時保護和資源清理

## 法律聲明

本工具僅供個人學習使用，請遵守以下原則：
- ✅ 僅使用自己的帳號
- ✅ 遵守平台使用條款
- ✅ 不進行任何違法活動
- ✅ 正確歸屬學習時數

作者不對任何濫用行為負責。

## 版本歷史

- **v1.0.0**: 初始版本
  - 基本登入和課程處理
  - 視頻播放和測驗作答
  - 條件動態提取
  - 加密帳密存儲

## 聯絡方式

如有問題或建議，請檢查日誌檔案並附上相關信息。