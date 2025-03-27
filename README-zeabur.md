# CryptoAnalyzer - Zeabur 部署指南

## 應用簡介

CryptoAnalyzer是一個整合了SMC(Smart Money Concept)和SNR(Support & Resistance)分析方法的加密貨幣技術分析工具。本應用使用DeepSeek V3的真實API進行技術分析，並模擬GPT-4o3-mini和Claude 3.7分析能力，提供全面的加密貨幣市場洞察。

## 部署步驟

### 方法一：直接從GitHub部署

1. 在GitHub上創建一個儲存庫，上傳以下文件：
   - `crypto_analyzer_ai.py` (主應用程式)
   - `requirements.txt` (依賴項)
   - `Procfile` (指定啟動命令)
   - `runtime.txt` (指定Python版本)

2. 登入 [Zeabur](https://dash.zeabur.com/)

3. 創建一個新項目

4. 點選「Deploy New Service」並選擇「GitHub」作為來源

5. 選擇您的GitHub儲存庫

6. Zeabur會自動偵測Procfile並進行部署

7. 部署完成後，點選「Domain」分配一個域名

### 方法二：使用Zeabur CLI

1. 安裝Zeabur CLI：
   ```
   npm install -g zeabur
   ```

2. 登入您的Zeabur帳戶：
   ```
   zeabur login
   ```

3. 導航至專案目錄：
   ```
   cd /path/to/your/project
   ```

4. 部署專案：
   ```
   zeabur deploy
   ```

## 環境變數設定

在Zeabur控制台的「Environment Variables」部分，設定以下環境變數：

- `DEEPSEEK_API_KEY`: 您的DeepSeek API金鑰

## 注意事項

1. Zeabur會自動根據`requirements.txt`安裝依賴項

2. 預設情況下，Streamlit會使用端口8501，但Zeabur會自動映射為您的應用分配的端口

3. 部署後，您需要確保API金鑰正確設定才能使用DeepSeek功能

## 故障排除

如果部署過程中遇到問題：

1. 檢查日誌：在Zeabur控制台查看部署和運行日誌

2. 確認`requirements.txt`包含所有必要依賴

3. 確保`Procfile`正確指定啟動命令

4. 如果應用需要較長時間啟動，可能需要增加啟動超時時間 