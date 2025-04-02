import streamlit as st
import pandas as pd
import numpy as np
import time
import random
from datetime import datetime, timedelta
import plotly.graph_objects as go
import requests
import json
import os
from openai import OpenAI
from dotenv import load_dotenv

# Streamlit頁面設定
st.set_page_config(
    page_title="CryptoAnalyzer - 簡易版",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="📊"
)

# 載入環境變數
load_dotenv()

# 初始化 OpenAI 客戶端 - 使用最簡單的方式
try:
    api_key = None
    # 嘗試從 Streamlit secrets 讀取
    if 'OPENAI_API_KEY' in st.secrets:
        api_key = st.secrets['OPENAI_API_KEY']
    # 嘗試從環境變數讀取
    elif os.environ.get('OPENAI_API_KEY'):
        api_key = os.environ.get('OPENAI_API_KEY')
    
    # 初始化 OpenAI 客戶端
    if api_key:
        client = OpenAI(api_key=api_key)
    else:
        client = None
        st.sidebar.warning("未找到 OpenAI API 密鑰，GPT-4 分析功能將不可用")
except Exception as e:
    client = None
    st.sidebar.error(f"初始化 OpenAI 客戶端時出錯: {str(e)}")

# 從 CoinGecko 獲取加密貨幣數據
def get_crypto_data(coin_id, days=30):
    try:
        url = f'https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart'
        params = {
            'vs_currency': 'usd',
            'days': days,
            'interval': 'daily' if days > 30 else None
        }
        
        response = requests.get(url, params=params)
        if response.status_code != 200:
            st.error(f"獲取數據失敗: {response.status_code}")
            return None
            
        data = response.json()
        
        # 處理數據
        prices = data['prices']  # [timestamp, price]
        volumes = data.get('total_volumes', [])  # [timestamp, volume]
        
        # 創建 DataFrame
        df_data = []
        for i in range(len(prices)):
            timestamp = prices[i][0]
            price = prices[i][1]
            volume = volumes[i][1] if i < len(volumes) else 0
            
            # 估算其他價格
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
        
        df = pd.DataFrame(df_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        st.error(f"獲取數據時出錯: {e}")
        return None

# 簡易分析函數
def simple_analysis(df):
    if df is None or len(df) < 5:
        return None
    
    # 計算基本指標
    latest_price = df['close'].iloc[-1]
    price_change = (latest_price - df['close'].iloc[-5]) / df['close'].iloc[-5] * 100
    trend = "上升" if price_change > 0 else "下降"
    
    # 計算支撐和阻力位
    support = df['low'].min() * 0.99
    resistance = df['high'].max() * 1.01
    
    results = {
        'price': latest_price,
        'change_percent': price_change,
        'trend': trend,
        'support': support,
        'resistance': resistance,
        'recommendation': 'buy' if trend == "上升" else 'sell'
    }
    
    return results

# GPT-4 分析函數
def get_gpt4_analysis(coin, df, analysis_results):
    if client is None:
        return "GPT-4 分析功能不可用: API 密鑰未設置"
    
    try:
        # 準備 prompt
        prompt = f"""
作為加密貨幣專家，請分析以下 {coin} 數據：
- 當前價格: ${analysis_results['price']:.2f}
- 價格變化: {analysis_results['change_percent']:.2f}%
- 趨勢: {analysis_results['trend']}
- 支撐位: ${analysis_results['support']:.2f}
- 阻力位: ${analysis_results['resistance']:.2f}

請提供市場分析和交易建議，包括風險評估。以繁體中文回答。
"""
        
        # 調用 API
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "你是加密貨幣分析專家，提供專業、簡潔的市場分析。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"GPT-4 API 調用失敗: {str(e)}")
        return f"無法獲取 GPT-4 分析: {str(e)}"

# 主界面
st.title("加密貨幣分析工具")

# 側邊欄
st.sidebar.title("設置")

# 選擇幣種
coins = {
    "Bitcoin (BTC)": "bitcoin",
    "Ethereum (ETH)": "ethereum",
    "Solana (SOL)": "solana",
    "Binance Coin (BNB)": "binancecoin",
    "Cardano (ADA)": "cardano",
    "Dogecoin (DOGE)": "dogecoin"
}

selected_coin_name = st.sidebar.selectbox("選擇幣種", list(coins.keys()))
selected_coin = coins[selected_coin_name]

# 選擇時間範圍
days_options = {
    "1 天": 1,
    "7 天": 7,
    "30 天": 30,
    "90 天": 90,
    "1 年": 365
}

selected_days_name = st.sidebar.selectbox("選擇時間範圍", list(days_options.keys()))
selected_days = days_options[selected_days_name]

# 分析按鈕
if st.sidebar.button("開始分析", use_container_width=True):
    # 獲取數據
    with st.spinner(f"獲取 {selected_coin_name} 數據..."):
        df = get_crypto_data(selected_coin, selected_days)
    
    if df is not None:
        # 顯示圖表
        st.subheader(f"{selected_coin_name} 價格走勢 ({selected_days_name})")
        fig = go.Figure(data=[go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close']
        )])
        fig.update_layout(xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
        
        # 基本分析
        analysis_results = simple_analysis(df)
        
        if analysis_results:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("基本分析")
                st.markdown(f"""
                - **當前價格**: ${analysis_results['price']:.2f}
                - **價格變化**: {analysis_results['change_percent']:.2f}%
                - **趨勢**: {analysis_results['trend']}
                - **支撐位**: ${analysis_results['support']:.2f}
                - **阻力位**: ${analysis_results['resistance']:.2f}
                - **建議**: {"買入" if analysis_results['recommendation'] == 'buy' else "賣出"}
                """)
            
            with col2:
                st.subheader("GPT-4 分析")
                with st.spinner("正在獲取 GPT-4 分析..."):
                    gpt4_analysis = get_gpt4_analysis(selected_coin_name, df, analysis_results)
                st.markdown(gpt4_analysis)
        else:
            st.error("無法進行分析，數據不足")
    else:
        st.error("無法獲取數據，請稍後再試")
else:
    # 顯示歡迎信息
    st.markdown("""
    ## 歡迎使用加密貨幣分析工具
    
    請從側邊欄選擇幣種和時間範圍，然後點擊「開始分析」按鈕獲取分析結果。
    
    這個工具使用:
    - CoinGecko API 獲取市場數據
    - 技術分析指標評估市場趨勢
    - GPT-4 提供專業的市場見解和交易建議
    
    **提示**: 由於 API 限制，免費版本可能有請求限制，如果遇到問題請稍後再試。
    """) 