import streamlit as st

# Streamlit頁面設定 - 必須是第一個 Streamlit 命令
st.set_page_config(
    page_title="CryptoAnalyzer - 加密貨幣分析工具",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="📊"
)

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

# 初始化 OpenAI 客戶端 - 不使用 proxies 參數
try:
    api_key = None
    if 'OPENAI_API_KEY' in st.secrets:
        api_key = st.secrets['OPENAI_API_KEY']
        st.sidebar.success("✓ 從 Streamlit secrets 讀取 OPENAI_API_KEY")
    elif os.getenv('OPENAI_API_KEY'):
        api_key = os.getenv('OPENAI_API_KEY')
        st.sidebar.success("✓ 從環境變數讀取 OPENAI_API_KEY")
    
    if api_key:
        # 純粹只使用 API 密鑰初始化，不添加任何其他參數
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

# 基本函數定義
def fetch_ohlcv_data(symbol, timeframe, limit=100):
    try:
        exchange = ccxt.binance()
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        st.error(f"獲取數據時出錯: {e}")
        return None

# GPT-4o 分析函數 - 確保不使用 proxies
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
        
        # 使用 GPT-4 API - 確保不使用任何額外參數如 proxies
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
    
    # 分析按鈕
    if st.sidebar.button("開始分析", use_container_width=True):
        # 獲取數據
        with st.spinner(f"獲取 {selected_coin} 數據..."):
            df = fetch_ohlcv_data(selected_coin, timeframe)
            
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
            st.plotly_chart(fig, use_container_width=True)
            
            # 顯示模擬分析結果
            st.subheader("分析結果")
            
            # 模擬結果
            smc_results = {
                'price': df['close'].iloc[-1],
                'market_structure': 'bullish' if df['close'].iloc[-1] > df['close'].iloc[-5] else 'bearish',
                'liquidity': 'normal',
                'support_level': df['low'].min() * 0.99,
                'resistance_level': df['high'].max() * 1.01,
                'trend_strength': 0.7,
                'recommendation': 'buy' if df['close'].iloc[-1] > df['close'].iloc[-5] else 'sell'
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
            
            # 顯示 GPT-4 分析結果
            st.subheader("GPT-4 進階市場分析")
            gpt4_analysis = get_gpt4o_analysis(selected_coin, timeframe, smc_results, snr_results)
            st.markdown(gpt4_analysis)
        else:
            st.error("無法獲取數據，請稍後再試")

if __name__ == "__main__":
    main()
