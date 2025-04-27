# Lovense AI 同步工具 🎮

這是一個能夠將影片內容自動轉換為 Lovense 玩具控制指令，並透過API同步影片操控玩具的工具。

## 功能特點 ✨

- 從 Pornhub 下載影片並提取音訊
- 使用 OpenAI Whisper 進行語音轉文字
- 智能分析內容並生成玩具控制指令
- 直觀的圖形使用者介面
- 支援多種 Lovense 玩具型號

## 系統需求 🔧

- Python 3.12
- FFmpeg
- OpenAI API 金鑰

## 安裝步驟 📦

1. 克隆此專案：
```bash
git clone [repository_url]
```

2. 安裝依賴：
```bash
pip install -r requirements.txt
```

3. 設置環境變數：
   - 建立 `.env` 檔案
   - 加入以下內容：
```
OPENAI_API_KEY=your_api_key_here
```

## 使用方法 📝

1. 執行主程式：
```bash
python UI_main.py
```

2. 在介面中輸入 Pornhub 影片網址或選擇本地檔案
3. 選擇目標玩具型號
4. 點擊相應按鈕開始處理

## 待完成項目 ⏳

- [ ] 新增進度條顯示下載和處理進度
- [ ] 新增玩具連線功能
- [ ] 新增玩具控制介面
- [ ] 新增播放器同步功能
- [ ] 新增多語言支援
- [ ] 優化音訊轉換效能
- [ ] 新增批次處理功能
- [ ] 新增錯誤處理和重試機制
- [ ] 新增使用者設定儲存功能
- [ ] 新增自動更新功能

## 注意事項 ⚠️

- 請確保您有足夠的硬碟空間
- 請勿濫用或進行非法用途
- 建議使用穩定的網路連線
- 請遵守相關法律法規

## 貢獻指南 🤝

歡迎提交 Pull Request 或建立 Issue。

## 授權協議 📄

本專案採用 MIT License 授權。

```
MIT License

Copyright (c) 2024 samttoo22-MewCat

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
