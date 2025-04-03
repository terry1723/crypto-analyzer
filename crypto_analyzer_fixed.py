import streamlit as st

import pandas as pd
import numpy as np
import ccxt
import time
import random
from datetime import datetime, timedelta
import plotly.graph_objects as go
import requests
import json
import os
from openai import OpenAI
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 初始化 OpenAI 客戶端 - 確保沒有任何額外參數
try:
    api_key = None
    if 'OPENAI_API_KEY' in st.secrets:
        api_key = st.secrets['OPENAI_API_KEY']
        st.sidebar.success("✓ 從 Streamlit secrets 讀取 OPENAI_API_KEY")
    elif os.getenv('OPENAI_API_KEY'):
        api_key = os.getenv('OPENAI_API_KEY')
        st.sidebar.success("✓ 從環境變數讀取 OPENAI_API_KEY")
    
    if api_key:
        # 最簡單的初始化方式，只使用 API 密鑰
        client = OpenAI(api_key=api_key)
        st.sidebar.success("✓ OpenAI 客戶端初始化成功")
    else:
        st.sidebar.warning("⚠ 未找到 OpenAI API 密鑰，GPT-4 分析功能將不可用")
        client = None
except Exception as e:
    st.sidebar.error(f"⚠ 初始化 OpenAI 客戶端時出錯: {str(e)}")
    client = None

# 從Streamlit secrets或環境變數讀取DeepSeek API密鑰
if 'DEEPSEEK_API_KEY' in st.secrets:
    DEEPSEEK_API_KEY = st.secrets['DEEPSEEK_API_KEY']
else:
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-6ae04d6789f94178b4053d2c42650b6c")

# Coincap API 基本 URL
COINCAP_API_URL = "http://localhost:3000/api"  # Coincap MCP 默認地址

# 基本函數定義
@st.cache_data(ttl=300)  # 緩存5分鐘，減少API請求
def fetch_ohlcv_data(symbol, timeframe, limit=100):
    try:
        # 將交易對格式從 Binance 轉換為 Coincap 格式
        # 例如：'BTC/USDT' -> 'bitcoin'
        coin_mapping = {
            'BTC/USDT': 'bitcoin',
            'ETH/USDT': 'ethereum',
            'SOL/USDT': 'solana',
            'BNB/USDT': 'binance-coin',
            'XRP/USDT': 'xrp',
            'ADA/USDT': 'cardano',
            'DOGE/USDT': 'dogecoin',
            'SHIB/USDT': 'shiba-inu'
        }
        
        # 將時間框架轉換為天數
        days_mapping = {
            '15m': 1,  # 1天內的數據
            '1h': 7,   # 7天內的數據
            '4h': 30,  # 30天內的數據
            '1d': 90,  # 90天內的數據
            '1w': 365  # 365天內的數據
        }
        
        if symbol not in coin_mapping:
            return dummy_data(symbol)  # 如果不支持的幣種，返回模擬數據
            
        coin_id = coin_mapping[symbol]
        
        # 嘗試使用 Coincap MCP 獲取加密貨幣價格數據
        try:
            # 首先獲取資產ID
            asset_response = requests.get(f"{COINCAP_API_URL}/assets/{coin_id}")
            if asset_response.status_code != 200:
                st.warning(f"無法從 Coincap 獲取 {coin_id} 資產信息，嘗試使用備用方式")
                return fallback_fetch_data(symbol, timeframe, limit)
                
            asset_data = asset_response.json()
            
            # 獲取歷史價格數據
            days = days_mapping.get(timeframe, 30)
            history_response = requests.get(
                f"{COINCAP_API_URL}/assets/{coin_id}/history", 
                params={"interval": "d1", "limit": limit}
            )
            
            if history_response.status_code != 200:
                st.warning(f"無法從 Coincap 獲取 {coin_id} 歷史數據，嘗試使用備用方式")
                return fallback_fetch_data(symbol, timeframe, limit)
                
            history_data = history_response.json()
            
            # 處理數據格式
            df_data = []
            for point in history_data.get("data", []):
                timestamp = int(point.get("time", 0))
                price = float(point.get("priceUsd", 0))
                volume = float(point.get("volumeUsd", 0))
                
                # 估算其他價格（因為 Coincap 只提供收盤價）
                open_price = price * 0.99
                high_price = price * 1.02
                low_price = price * 0.98
                
                df_data.append([
                    timestamp,
                    open_price,
                    high_price,
                    low_price,
                    price,
                    volume
                ])
            
            # 如果沒有數據，使用備用方法
            if not df_data:
                st.warning(f"Coincap 返回的 {coin_id} 數據為空，嘗試使用備用方式")
                return fallback_fetch_data(symbol, timeframe, limit)
                
            # 創建 DataFrame
            df = pd.DataFrame(df_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # 排序並限制數據數量
            df = df.sort_values('timestamp')
            if len(df) > limit:
                df = df.tail(limit)
                
            st.success(f"成功從 Coincap 獲取 {symbol} 的數據")
            return df
            
        except Exception as e:
            st.warning(f"使用 Coincap 獲取數據時出錯: {e}，嘗試使用備用方式")
            return fallback_fetch_data(symbol, timeframe, limit)
            
    except Exception as e:
        st.error(f"獲取數據時出錯: {e}")
        return dummy_data(symbol)  # 發生任何錯誤時返回模擬數據

# 備用數據獲取方法（使用 CoinGecko）
def fallback_fetch_data(symbol, timeframe, limit=100):
    try:
        st.info("使用 CoinGecko API 作為備用數據源...")
        
        # 將交易對格式從 Binance 轉換為 CoinGecko 格式
        coin_mapping = {
            'BTC/USDT': 'bitcoin',
            'ETH/USDT': 'ethereum',
            'SOL/USDT': 'solana',
            'BNB/USDT': 'binancecoin',
            'XRP/USDT': 'ripple',
            'ADA/USDT': 'cardano',
            'DOGE/USDT': 'dogecoin',
            'SHIB/USDT': 'shiba-inu'
        }
        
        # 將時間框架轉換為天數
        days_mapping = {
            '15m': 1,  # 1天內的數據（15分鐘粒度）
            '1h': 7,   # 7天內的數據（1小時粒度）
            '4h': 30,  # 30天內的數據（4小時粒度）
            '1d': 90,  # 90天內的數據（1天粒度）
            '1w': 365  # 365天內的數據（1週粒度）
        }
        
        if symbol not in coin_mapping:
            return dummy_data(symbol)
            
        coin_id = coin_mapping[symbol]
        days = days_mapping.get(timeframe, 30)
        
        # 使用CoinGecko API獲取市場數據
        url = f'https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart'
        params = {
            'vs_currency': 'usd',
            'days': days,
            'interval': 'daily' if timeframe in ['1d', '1w'] else None
        }
        
        # 添加重試機制，最多嘗試3次
        max_retries = 3
        retry_delay = 2  # 初始延遲2秒
        
        for retry in range(max_retries):
            # 添加隨機延遲，緩解API請求頻率
            if retry > 0:
                # 使用指數退避策略增加延遲
                delay = retry_delay * (2 ** retry) + random.uniform(0, 1)
                st.info(f"API請求失敗，{delay:.1f}秒後重試 ({retry+1}/{max_retries})...")
                time.sleep(delay)
            
            response = requests.get(url, params=params, 
                                   headers={'User-Agent': 'CryptoAnalyzer/1.0'})
            
            # 檢查是否成功
            if response.status_code == 200:
                data = response.json()
                break
            # 如果是速率限制錯誤(429)，進行重試
            elif response.status_code == 429:
                if retry == max_retries - 1:  # 最後一次嘗試
                    st.warning(f"獲取CoinGecko數據時出錯: 429（請求過多）- 已達到API限制")
                    return dummy_data(symbol)
                continue
            # 其他錯誤直接返回模擬數據
            else:
                st.error(f"獲取數據失敗: {response.status_code}")
                return dummy_data(symbol)
        
        # 如果所有重試都失敗，返回模擬數據
        if 'data' not in locals():
            st.warning("所有API請求嘗試均失敗，使用模擬數據")
            return dummy_data(symbol)
            
        # 轉換數據格式
        prices = data['prices']  # [timestamp, price]
        volumes = data.get('total_volumes', [])  # [timestamp, volume]
        
        # 將數據組織成DataFrame
        df_data = []
        for i in range(len(prices)):
            timestamp = prices[i][0]
            price = prices[i][1]
            volume = volumes[i][1] if i < len(volumes) else 0
            
            # 在CoinGecko API中我們只有收盤價，所以我們用收盤價估算其他價格
            open_price = price * 0.99  # 估算開盤價
            high_price = price * 1.02  # 估算最高價
            low_price = price * 0.98   # 估算最低價
            
            df_data.append([
                timestamp,
                open_price,
                high_price,
                low_price,
                price,
                volume
            ])
        
        df = pd.DataFrame(df_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # 限制返回的行數
        if len(df) > limit:
            df = df.tail(limit)
            
        return df
    except Exception as e:
        st.error(f"備用數據獲取出錯: {e}")
        return dummy_data(symbol)

# 在無法獲取真實數據時生成模擬數據
def dummy_data(symbol, periods=100):
    st.warning(f"無法從 API 獲取 {symbol} 的數據，使用模擬數據進行演示。")
    
    # 生成時間戳列表
    end_date = datetime.now()
    start_date = end_date - timedelta(days=periods)
    dates = pd.date_range(start=start_date, end=end_date, periods=periods)
    
    # 生成隨機價格數據，模擬加密貨幣的波動性
    base_price = 100.0 if 'BTC' not in symbol else 30000.0
    volatility = 0.02
    
    price_data = [base_price]
    for i in range(1, periods):
        change = np.random.normal(0, volatility)
        price = price_data[-1] * (1 + change)
        price_data.append(price)
    
    # 創建DataFrame
    df = pd.DataFrame({
        'timestamp': dates,
        'open': [p * (1 - 0.005 * np.random.random()) for p in price_data],
        'high': [p * (1 + 0.01 * np.random.random()) for p in price_data],
        'low': [p * (1 - 0.01 * np.random.random()) for p in price_data],
        'close': price_data,
        'volume': [np.random.random() * 1000000 for _ in range(periods)]
    })
    
    return df

# GPT-4o 分析函數
def get_gpt4o_analysis(symbol, timeframe, smc_results, snr_results):
    try:
        # 檢查 OpenAI 客戶端是否可用
        if client is None:
            st.warning("OpenAI 客戶端未初始化或初始化失敗")
            raise Exception("OpenAI 客戶端未初始化或初始化失敗")
        
        st.info("正在準備連接 OpenAI API...")
        
        # 準備分析內容
        prompt = f"""
作為一個專業的加密貨幣分析師，請基於以下數據對 {symbol} 進行深入分析：

時間框架: {timeframe}

SMC分析結果:
- 當前價格: ${smc_results['price']}
- 市場結構: {smc_results['market_structure']}
- 流動性: {smc_results['liquidity']}
- 支撐位: ${smc_results['support_level']}
- 阻力位: ${smc_results['resistance_level']}
- 趨勢強度: {smc_results['trend_strength']}
- SMC建議: {smc_results['recommendation']}

SNR分析結果:
- RSI: {snr_results['rsi']}
- 超買狀態: {snr_results['overbought']}
- 超賣狀態: {snr_results['oversold']}
- 近期支撐: ${snr_results['near_support']}
- 強力支撐: ${snr_results['strong_support']}
- 近期阻力: ${snr_results['near_resistance']}
- 強力阻力: ${snr_results['strong_resistance']}
- 支撐強度: {snr_results['support_strength']}
- 阻力強度: {snr_results['resistance_strength']}
- SNR建議: {snr_results['recommendation']}

請提供：
1. 市場狀況綜合分析
2. 潛在的交易機會
3. 風險評估
4. 建議的交易策略
5. 關鍵價位和止損止盈建議

請用繁體中文回答，並保持專業、簡潔和實用性。
"""

        st.info("正在連接 OpenAI API，這可能需要幾秒鐘...")
        
        # 最簡單的 API 調用方式
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "你是一個專業的加密貨幣分析師，擅長技術分析和風險管理。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        st.success("成功連接到 OpenAI API 並獲得回應！")
        
        if not response.choices:
            raise Exception("GPT-4 API 未返回有效回應")
            
        return response.choices[0].message.content
            
    except Exception as e:
        error_message = f"GPT-4 API 調用失敗：{str(e)}"
        st.error(error_message)
        st.error(f"詳細錯誤信息：{type(e).__name__}: {str(e)}")
        
        if "unsupported_country_region_territory" in str(e):
            st.warning("地區限制錯誤：您的網絡地址可能受到 OpenAI 的地區限制。請確保 VPN 已正確設置。")
        
        if client is None:
            st.warning("OpenAI 客戶端為空：請檢查 API 密鑰設置。")
            
        return f"""
## GPT-4 分析暫時無法使用

**錯誤信息**: {error_message}

請檢查以下可能的問題：
1. API 密鑰是否正確設置
2. 網絡連接是否正常
3. VPN 是否正確配置

目前 API 密鑰狀態：{"已設置" if client else "未設置"}
"""

# 基本頁面顯示
st.title("CryptoAnalyzer - 加密貨幣專業分析工具")
st.markdown("### 整合SMC和SNR策略的AI輔助分析系統")

# 簡化的主應用邏輯
def main():
    # 側邊欄 - 設定選項
    st.sidebar.title("分析設定")
    
    # 幣種選擇
    COINS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT", "DOGE/USDT", "SHIB/USDT"]
    selected_coin = st.sidebar.selectbox("選擇幣種", COINS)
    
    # 時間範圍選擇
    TIMEFRAMES = {
        "15分鐘": "15m",
        "1小時": "1h", 
        "4小時": "4h",
        "1天": "1d",
        "1週": "1w"
    }
    selected_timeframe = st.sidebar.selectbox("選擇時間範圍", list(TIMEFRAMES.keys()))
    timeframe = TIMEFRAMES[selected_timeframe]
    
    # 高級設置區
    with st.sidebar.expander("高級設置", expanded=False):
        use_dummy_data = st.checkbox("使用模擬數據", value=False, 
                                    help="選中此項將始終使用模擬數據，避免API限制問題")
        show_warnings = st.checkbox("顯示警告信息", value=True,
                                   help="顯示API請求相關的警告信息")
    
    # 分析按鈕
    if st.sidebar.button("開始分析", use_container_width=True):
        # 獲取數據
        with st.spinner(f"獲取 {selected_coin} 數據..."):
            if use_dummy_data:
                st.info("使用模擬數據進行分析")
                df = dummy_data(selected_coin)
            else:
                df = fetch_ohlcv_data(selected_coin, timeframe)
                
                # 如果不顯示警告，清除之前的警告信息
                if not show_warnings:
                    # 清除警告信息（這個方法在某些Streamlit版本可能不完全有效）
                    for element in st.empty():
                        if isinstance(element, st._DeltaGenerator) and hasattr(element, '_is_warning'):
                            element.empty()
            
        if df is not None:
            # 顯示簡單的圖表
            st.subheader(f"{selected_coin} {selected_timeframe} 圖表")
            fig = go.Figure(data=[go.Candlestick(
                x=df['timestamp'],
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close']
            )])
            
            # 改進圖表顯示
            fig.update_layout(
                xaxis_rangeslider_visible=False,
                height=500,
                margin=dict(l=50, r=50, t=30, b=50),
                yaxis_title="價格 (USD)",
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 顯示模擬分析結果
            st.subheader("分析結果")
            
            # 準備分析結果
            last_price = df['close'].iloc[-1]
            trend_days = min(5, len(df)-1)  # 確保不會超出數據範圍
            
            # 模擬結果
            smc_results = {
                'price': last_price,
                'market_structure': 'bullish' if df['close'].iloc[-1] > df['close'].iloc[-trend_days] else 'bearish',
                'liquidity': 'normal',
                'support_level': df['low'].min() * 0.99,
                'resistance_level': df['high'].max() * 1.01,
                'trend_strength': 0.7,
                'recommendation': 'buy' if df['close'].iloc[-1] > df['close'].iloc[-trend_days] else 'sell'
            }
            
            snr_results = {
                'rsi': 55,
                'overbought': False,
                'oversold': False,
                'near_support': df['low'].min() * 0.99,
                'strong_support': df['low'].min() * 0.98,
                'near_resistance': df['high'].max() * 1.01,
                'strong_resistance': df['high'].max() * 1.02,
                'support_strength': 0.6,
                'resistance_strength': 0.7,
                'recommendation': 'neutral'
            }
            
            # 顯示簡單分析結果
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                #### SMC分析
                - **當前價格**: ${smc_results['price']:.2f}
                - **市場結構**: {smc_results['market_structure']}
                - **支撐位**: ${smc_results['support_level']:.2f}
                - **阻力位**: ${smc_results['resistance_level']:.2f}
                - **建議**: {smc_results['recommendation']}
                """)
            
            with col2:
                st.markdown(f"""
                #### SNR分析
                - **RSI**: {snr_results['rsi']}
                - **近期支撐**: ${snr_results['near_support']:.2f}
                - **近期阻力**: ${snr_results['near_resistance']:.2f}
                - **建議**: {snr_results['recommendation']}
                """)
            
            # 顯示 GPT-4 分析結果
            with st.expander("GPT-4 進階市場分析", expanded=True):
                gpt4_analysis = get_gpt4o_analysis(selected_coin, timeframe, smc_results, snr_results)
                st.markdown(gpt4_analysis)
        else:
            st.error("無法獲取數據，請檢查網絡連接或選擇其他交易對。")
            st.info("您可以在「高級設置」中選擇「使用模擬數據」選項來繞過API限制。")
    else:
        # 顯示應用程式說明
        st.markdown("""
        ## 歡迎使用加密貨幣分析工具
        
        請從側邊欄選擇幣種和時間範圍，然後點擊「開始分析」按鈕獲取分析結果。
        
        ### 使用說明
        
        1. **選擇幣種**：從側邊欄選擇要分析的加密貨幣
        2. **選擇時間範圍**：選擇分析的時間框架
        3. **高級設置**：調整應用程式行為，包括使用模擬數據選項
        4. **點擊「開始分析」**：獲取市場分析結果
        
        ### 關於API限制
        
        本應用使用 CoinGecko 免費 API 獲取市場數據，該 API 有請求頻率限制：
        
        - 如果遇到 429 錯誤(請求過多)，應用將自動重試
        - 如果仍無法獲取數據，將使用模擬數據進行演示
        - 您可以在「高級設置」中選擇始終使用模擬數據，避免API限制問題
        
        了解更多關於 [CoinGecko API 限制](https://www.coingecko.com/en/api/documentation)
        """)

if __name__ == "__main__":
    main()
