# CryptoAnalyzer

加密貨幣專業分析工具，整合SMC和SNR策略的多模型AI輔助分析系統。

## 功能特點

- SMC（Smart Money Concept）策略分析
- SNR（Support & Resistance）策略分析
- 使用真實 GPT-4o3-mini API 進行市場情緒分析
- DeepSeek V3 全方位技術分析
- 多模型AI集成分析
- 即時市場數據分析
- 詳細的技術指標可視化

## 部署平台

此項目已配置為在Zeabur上部署的雲端應用。

## 部署說明

### Zeabur 部署流程

1. 在 [Zeabur](https://zeabur.com) 上註冊並創建一個新項目
2. 將此代碼庫連接到您的 Zeabur 項目
3. 設置以下環境變數：
   - `DEEPSEEK_API_KEY`：DeepSeek API 密鑰
   - `COINMARKETCAP_API_KEY`：CoinMarketCap API 密鑰
   - `OPENAI_API_KEY`：OpenAI API 密鑰（用於 GPT-4o3-mini 市場情緒分析）
4. 部署應用程序

部署配置已在 `zeabur.json` 和 `zeabur.toml` 文件中設置好。

### 本地運行

1. 克隆此代碼庫
2. 安裝依賴項：`pip install -r requirements.txt`
3. 創建 `.env` 文件並設置必要的環境變數（參見 `.env.example`）
4. 運行應用程序：`streamlit run app.py`

## API 來源

應用程序使用以下 API 來源獲取加密貨幣數據：

1. Coincap API（主要）
2. CoinMarketCap API（第一備份）
3. Bitget API（第二備份）
4. Coinbase API（第三備份）
5. 模擬數據（最終備份）

此多層備份策略確保應用程序在任何 API 不可用時都能繼續運行。

## AI 模型

應用程序使用以下 AI 模型進行分析：

1. DeepSeek V3：進行技術分析
2. GPT-4o3-mini：進行市場情緒分析
3. 模擬 Claude 3.7：進行整合分析 