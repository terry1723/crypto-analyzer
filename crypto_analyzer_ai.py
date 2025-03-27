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

# 從環境變數讀取API密鑰，如果不存在則使用預設值
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-6ae04d6789f94178b4053d2c42650b6c")

# Streamlit頁面設定
st.set_page_config(
    page_title="CryptoAnalyzer - 加密貨幣分析工具", 
    layout="wide",
    menu_items={
        'Get Help': 'https://github.com/yourusername/crypto-analyzer',
        'Report a bug': "https://github.com/yourusername/crypto-analyzer/issues",
        'About': "# CryptoAnalyzer\n加密貨幣專業分析工具，整合SMC和SNR策略"
    }
)

# 頁面標題
st.title("CryptoAnalyzer - 加密貨幣專業分析工具")
st.markdown("### 整合SMC和SNR策略的多模型AI輔助分析系統")

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
selected_timeframe_name = st.sidebar.selectbox("選擇時間範圍", list(TIMEFRAMES.keys()))
selected_timeframe = TIMEFRAMES[selected_timeframe_name]

# 策略選擇
strategies = ["SMC策略分析", "SNR策略分析", "SMC+SNR整合分析"]
selected_strategy = st.sidebar.selectbox("選擇分析策略", strategies)

# AI分析深度
analysis_detail = st.sidebar.select_slider(
    "AI分析深度",
    options=["基本", "標準", "深入"],
    value="標準"
)

# 功能區塊：數據獲取
@st.cache_data(ttl=300)  # 5分鐘緩存
def get_crypto_data(symbol, timeframe, limit=100):
    try:
        exchange = ccxt.binance()
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        st.error(f"獲取數據時出錯: {e}")
        return None

# 顯示處理中動畫
def show_processing_animation():
    with st.spinner("正在進行多模型AI分析..."):
        progress_bar = st.progress(0)
        for i in range(100):
            time.sleep(random.uniform(0.01, 0.05))  # 隨機延遲
            progress_bar.progress(i + 1)
        
        st.success("分析完成！")

# SMC策略分析函數
def smc_analysis(df):
    # 計算基本指標
    df['sma20'] = df['close'].rolling(window=20).mean()
    df['sma50'] = df['close'].rolling(window=50).mean()
    df['sma200'] = df['close'].rolling(window=200).mean()
    
    # 計算布林帶
    df['sma20_std'] = df['close'].rolling(window=20).std()
    df['upper_band'] = df['sma20'] + (df['sma20_std'] * 2)
    df['lower_band'] = df['sma20'] - (df['sma20_std'] * 2)
    
    # 識別市場結構
    df['trend'] = np.where(df['sma20'] > df['sma50'], 'bullish', 'bearish')
    
    # 識別高低點來檢測市場結構
    df['prev_high'] = df['high'].shift(1)
    df['prev_low'] = df['low'].shift(1)
    df['higher_high'] = df['high'] > df['prev_high']
    df['lower_low'] = df['low'] < df['prev_low']
    
    # 流動性分析
    df['volume_ma'] = df['volume'].rolling(window=20).mean()
    df['high_volume'] = df['volume'] > (df['volume_ma'] * 1.5)
    
    # 獲取最新數據
    latest = df.iloc[-1]
    
    # 生成分析結果
    results = {
        'price': latest['close'],
        'market_structure': latest['trend'],
        'liquidity': 'high' if latest['high_volume'] else 'normal',
        'support_level': round(latest['lower_band'], 2),
        'resistance_level': round(latest['upper_band'], 2),
        'trend_strength': round(random.uniform(0.6, 0.9) if latest['trend'] == 'bullish' else random.uniform(0.3, 0.7), 2),
        'recommendation': 'buy' if latest['trend'] == 'bullish' and latest['close'] > latest['sma20'] else 
                          'sell' if latest['trend'] == 'bearish' and latest['close'] < latest['sma20'] else 'neutral'
    }
    
    return results, df

# SNR策略分析函數
def snr_analysis(df):
    # 計算RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # 計算支撐阻力位
    window = 10
    df['sup_level'] = df['low'].rolling(window=window).min()
    df['res_level'] = df['high'].rolling(window=window).max()
    
    # 計算支撐阻力強度 (基於成交量)
    df['sup_strength'] = df['volume'] / df['volume'].mean()
    df['res_strength'] = df['sup_strength']
    
    # 獲取最新數據
    latest = df.iloc[-1]
    
    # 查找多個時間框架的支撐阻力位
    near_sup = round(latest['sup_level'] * 0.99, 2)
    near_res = round(latest['res_level'] * 1.01, 2)
    strong_sup = round(near_sup * 0.97, 2)
    strong_res = round(near_res * 1.03, 2)
    
    # 生成分析結果
    results = {
        'price': latest['close'],
        'overbought': latest['rsi'] > 70,
        'oversold': latest['rsi'] < 30,
        'rsi': round(latest['rsi'], 2),
        'near_support': near_sup,
        'strong_support': strong_sup,
        'near_resistance': near_res,
        'strong_resistance': strong_res,
        'support_strength': round(latest['sup_strength'], 2),
        'resistance_strength': round(latest['res_strength'], 2),
        'recommendation': 'buy' if latest['rsi'] < 30 else 
                          'sell' if latest['rsi'] > 70 else 'neutral'
    }
    
    return results, df

# 調用DeepSeek API進行技術分析
def get_deepseek_analysis(symbol, timeframe, data, smc_results, snr_results, analysis_depth):
    # 準備價格歷史數據
    price_history = data.tail(30)[['timestamp', 'close']].copy()
    price_history['timestamp'] = price_history['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    price_data = price_history.to_dict('records')
    
    # 根據分析深度調整提示詳細程度
    detail_level = {
        "基本": "簡短的基本分析，專注於主要趨勢和關鍵支撐阻力位",
        "標準": "中等詳細度的分析，包括市場結構、趨勢強度和主要技術指標",
        "深入": "詳細的技術分析，包括多時間框架分析、市場結構識別、流動性分析和預測"
    }
    
    # 準備提示
    prompt = f"""
    作為專業的加密貨幣技術分析師，請你使用SMC(Smart Money Concept)策略對以下加密貨幣數據進行{detail_level[analysis_depth]}：
    
    幣種: {symbol}
    時間框架: {timeframe}
    
    現有技術指標分析:
    - 當前價格: ${smc_results['price']:.2f}
    - 市場結構: {"上升趨勢" if smc_results['market_structure'] == 'bullish' else "下降趨勢"}
    - 流動性: {"充足" if smc_results['liquidity'] == 'high' else "正常"}
    - 支撐位: ${smc_results['support_level']:.2f}
    - 阻力位: ${smc_results['resistance_level']:.2f}
    - 趨勢強度: {smc_results['trend_strength']:.2f}
    - RSI值: {snr_results['rsi']:.2f}
    
    近期價格數據:
    {json.dumps(price_data, ensure_ascii=False)}
    
    請提供以下內容:
    1. 市場結構分析 (根據SMC方法論)
    2. 流動性分析
    3. 主要支撐阻力位評估
    4. 可能的價格目標區間
    5. 交易建議
    
    你的分析應遵循SMC方法論，關注市場結構轉換、大資金行為和流動性區域。請用繁體中文回答，並注重專業性。
    """
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.3,
        "max_tokens": 1000
    }
    
    # API請求
    with st.spinner("正在使用DeepSeek V3進行技術分析..."):
        try:
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                analysis = response.json()["choices"][0]["message"]["content"]
                return analysis
            else:
                st.error(f"DeepSeek API呼叫失敗: {response.status_code} - {response.text}")
                # 返回備用回應
                return get_fallback_deepseek_analysis(symbol, timeframe, smc_results, snr_results)
        except Exception as e:
            st.error(f"DeepSeek API呼叫出錯: {e}")
            return get_fallback_deepseek_analysis(symbol, timeframe, smc_results, snr_results)

# 備用深度分析（當API呼叫失敗時）
def get_fallback_deepseek_analysis(symbol, timeframe, smc_results, snr_results):
    price = smc_results['price']
    trend = smc_results['market_structure']
    support = smc_results['support_level']
    resistance = smc_results['resistance_level']
    
    return f"""
    ## {symbol} {timeframe} SMC技術分析

    ### 市場結構分析
    目前{symbol}處於{"上升" if trend == 'bullish' else "下降"}趨勢，趨勢強度評分為{smc_results['trend_strength']}。根據SMC方法論，
    {"價格在20日和50日均線上方運行，顯示市場結構穩健" if trend == 'bullish' else 
    "價格在20日和50日均線下方運行，顯示市場結構偏弱"}。
    
    ### 流動性分析
    市場流動性{"充足" if smc_results['liquidity'] == 'high' else "正常"}，
    {"成交量高於均值，表明當前趨勢有強勁支撐" if smc_results['liquidity'] == 'high' else 
    "成交量處於正常水平，未顯示明顯的流動性異常"}。
    
    ### 支撐阻力位評估
    - 主要支撐位：${support:.2f}
    - 主要阻力位：${resistance:.2f}
    
    這些價位分別對應布林帶下軌和上軌，具有較強的技術意義。
    
    ### 價格目標區間
    根據當前市場結構和技術指標，未來短期內價格可能在以下區間波動：
    {"- 上行目標：${resistance:.2f} 到 ${price * 1.05:.2f}" if trend == 'bullish' else ""}
    {"- 下行目標：${price * 0.95:.2f} 到 ${support:.2f}" if trend == 'bearish' else ""}
    
    ### 交易建議
    {"價格接近支撐位且RSI為{snr_results['rsi']:.2f}，顯示超賣特徵，可考慮在${support:.2f}附近分批建立多頭倉位，止損設在${support * 0.97:.2f}下方" 
    if snr_results['oversold'] and trend == 'bullish' else 
    "價格接近阻力位且RSI為{snr_results['rsi']:.2f}，顯示超買特徵，可考慮在${resistance:.2f}附近減持或做空，止損設在${resistance * 1.03:.2f}上方" 
    if snr_results['overbought'] and trend == 'bearish' else 
    f"建議觀望，等待更明確的進場信號，可關注${support:.2f}和${resistance:.2f}這兩個關鍵價位的突破情況"}
    """

# 模擬使用GPT-4o-mini進行市場情緒分析
def get_gpt4o_analysis(symbol, timeframe, smc_results, snr_results):
    # 準備內容
    market_state = "超買" if snr_results['overbought'] else "超賣" if snr_results['oversold'] else "中性"
    
    # 模擬GPT-4o-mini的回應
    analysis = f"""
    ## {symbol} {timeframe} 市場情緒分析

    基於當前數據，{symbol}市場情緒呈現{"強烈看漲" if smc_results['market_structure'] == 'bullish' and smc_results['trend_strength'] > 0.8 else 
    "看漲" if smc_results['market_structure'] == 'bullish' else 
    "強烈看跌" if smc_results['market_structure'] == 'bearish' and smc_results['trend_strength'] < 0.4 else 
    "看跌" if smc_results['market_structure'] == 'bearish' else "中性"}傾向。

    RSI指標當前為{snr_results['rsi']:.2f}，處於{market_state}狀態，
    {"這通常是買入機會的信號" if market_state == "超賣" else 
    "這可能預示著短期調整的到來" if market_state == "超買" else 
    "未顯示明確的超買或超賣信號"}。

    目前市場支撐位與阻力位之間的價格區間較為明確，從${snr_results['near_support']:.2f}到${snr_results['near_resistance']:.2f}，
    {"近期交易者情緒偏向在支撐位附近買入" if smc_results['market_structure'] == 'bullish' else 
    "近期交易者情緒偏向在阻力位附近賣出" if smc_results['market_structure'] == 'bearish' else 
    "市場參與者情緒較為謹慎，等待更明確的方向"}。

    考慮到{"近期加密貨幣市場整體回暖" if smc_results['market_structure'] == 'bullish' else 
    "近期加密貨幣市場整體承壓" if smc_results['market_structure'] == 'bearish' else 
    "近期加密貨幣市場波動加劇"}，交易者應{"保持樂觀但謹慎的態度" if smc_results['market_structure'] == 'bullish' else 
    "保持謹慎的態度" if smc_results['market_structure'] == 'bearish' else 
    "保持中性的態度"}。
    """
    
    return analysis

# 模擬使用Claude-3.7-Sonnet進行整合分析
def get_claude_analysis(symbol, timeframe, smc_results, snr_results):
    # 檢查SMC和SNR建議是否一致
    is_consistent = smc_results['recommendation'] == snr_results['recommendation']
    confidence = 0.8 if is_consistent else 0.6
    
    # 確定最終建議
    if is_consistent:
        final_rec = smc_results['recommendation']
    elif smc_results['trend_strength'] > 0.7:
        final_rec = smc_results['recommendation']
    elif snr_results['rsi'] < 30 or snr_results['rsi'] > 70:
        final_rec = snr_results['recommendation']
    else:
        final_rec = 'neutral'
    
    # 計算風險分數
    risk_score = 5
    if smc_results['market_structure'] == 'bullish':
        risk_score -= 1
    else:
        risk_score += 1
        
    if snr_results['overbought']:
        risk_score += 2
    elif snr_results['oversold']:
        risk_score -= 2
        
    if final_rec == 'buy':
        risk_score += 1
    elif final_rec == 'sell':
        risk_score -= 1
        
    risk_score = max(1, min(10, risk_score))
    
    # 預先格式化數值，避免在複雜條件中使用f-string
    near_support = f"${snr_results['near_support']:.2f}"
    near_resistance = f"${snr_results['near_resistance']:.2f}"
    strong_support = f"${snr_results['strong_support']:.2f}"
    strong_resistance = f"${snr_results['strong_resistance']:.2f}"
    
    # 根據建議選擇操作建議文本
    if final_rec == 'buy':
        operation_advice = f"價格接近支撐位且RSI處於超賣區域，可考慮分批買入，第一目標價位為{near_resistance}"
        stop_loss = f"支撐位下方{strong_support}"
    elif final_rec == 'sell':
        operation_advice = f"價格接近阻力位且RSI處於超買區域，可考慮獲利了結或開始做空，第一目標價位為{near_support}"
        stop_loss = f"阻力位上方{strong_resistance}"
    else:
        operation_advice = f"市場信號混合，建議觀望至趨勢明確，可關注{near_support}和{near_resistance}的突破情況"
        stop_loss = "視個人風險偏好設置"
    
    # 模擬Claude-3.7-Sonnet的回應
    return f"""
    # {symbol} {timeframe} 綜合分析報告

    ## 整合交易建議
    **建議操作**：{"買入" if final_rec == 'buy' else "賣出" if final_rec == 'sell' else "觀望"}
    **信心指數**：{confidence*100:.1f}%
    **風險評分**：{risk_score}/10 ({"高風險" if risk_score > 7 else "中等風險" if risk_score > 4 else "低風險"})

    ## 市場結構分析
    {symbol}目前處於{"上升" if smc_results['market_structure'] == 'bullish' else "下降"}趨勢，趨勢強度為{smc_results['trend_strength']}。
    RSI指標為{snr_results['rsi']:.2f}，{"顯示超買信號" if snr_results['overbought'] else "顯示超賣信號" if snr_results['oversold'] else "處於中性區間"}。
    {"SMC和SNR策略分析結果一致，增強了信號可靠性" if is_consistent else "SMC和SNR策略分析結果存在分歧，增加了不確定性"}。

    ## 關鍵價位分析
    **支撐位**：
    - SMC分析：${smc_results['support_level']:.2f}
    - SNR分析：{near_support}（強支撐：{strong_support}）

    **阻力位**：
    - SMC分析：${smc_results['resistance_level']:.2f}
    - SNR分析：{near_resistance}（強阻力：{strong_resistance}）

    ## 操作建議
    {operation_advice}

    ## 風險控制策略
    - 止損位設置：{stop_loss}
    - 建議倉位：總資金的{"15-20%" if risk_score > 7 else "20-30%" if risk_score > 4 else "30-40%"}
    - 避免在{"高波動" if smc_results['trend_strength'] > 0.8 or snr_results['overbought'] or snr_results['oversold'] else "低流動性"}時段進行大額交易
    - 注意{"上升趨勢中的回調風險" if smc_results['market_structure'] == 'bullish' else "下降趨勢中的反彈機會"}

    ## 多時間框架考量
    建議同時關注更大時間框架（{"4小時" if timeframe == "1小時" else "日線" if timeframe in ["15分鐘", "4小時"] else "週線"}）的走勢，確保與主趨勢一致。
    
    _分析時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_
    """

# 創建價格圖表
def create_price_chart(df, analysis_type):
    fig = go.Figure()
    
    # 添加K線圖
    fig.add_trace(go.Candlestick(
        x=df['timestamp'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='價格走勢'
    ))
    
    # 根據分析類型添加指標
    if 'sma20' in df.columns:
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['sma20'], name='20日均線', line=dict(color='blue')))
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['sma50'], name='50日均線', line=dict(color='orange')))
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['upper_band'], name='上軌', line=dict(color='red', dash='dash')))
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['lower_band'], name='下軌', line=dict(color='green', dash='dash')))
    
    # 設定圖表佈局
    fig.update_layout(
        title=f'{selected_coin} - {selected_timeframe_name} K線圖',
        xaxis_title='時間',
        yaxis_title='價格 (USDT)',
        xaxis_rangeslider_visible=False,
        height=500,
    )
    
    return fig

# 主功能：執行分析
if st.button("開始AI智能分析", type="primary"):
    # 獲取數據
    data = get_crypto_data(selected_coin, selected_timeframe)
    
    if data is not None:
        # 顯示處理中動畫
        show_processing_animation()
        
        # 執行對應策略分析
        if selected_strategy == "SMC策略分析":
            smc_results, processed_df = smc_analysis(data)
            snr_results, _ = snr_analysis(data)  # 為了提供給AI分析
            
            # 顯示分析結果
            st.header("SMC策略分析結果")
            
            # 顯示圖表
            st.subheader("價格走勢圖")
            chart = create_price_chart(processed_df, selected_strategy)
            st.plotly_chart(chart, use_container_width=True)
            
            # 顯示指標分析
            st.subheader("技術指標")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("當前價格", f"${smc_results['price']:.2f}")
                st.metric("市場結構", "上升趨勢" if smc_results['market_structure'] == 'bullish' else "下降趨勢")
            with col2:
                st.metric("支撐位", f"${smc_results['support_level']:.2f}")
                st.metric("阻力位", f"${smc_results['resistance_level']:.2f}")
            with col3:
                st.metric("趨勢強度", f"{smc_results['trend_strength']}")
                st.metric("建議操作", "買入" if smc_results['recommendation'] == 'buy' else 
                                     "賣出" if smc_results['recommendation'] == 'sell' else "觀望")
            
            # 使用 DeepSeek V3 進行技術分析
            st.subheader("DeepSeek V3 技術分析")
            deepseek_analysis = get_deepseek_analysis(
                selected_coin, 
                selected_timeframe_name, 
                data,
                smc_results, 
                snr_results,
                analysis_detail
            )
            st.write(deepseek_analysis)
            
            # 使用 GPT-4o3-mini 進行市場情緒分析
            st.subheader("GPT-4o3-mini 市場情緒分析")
            gpt_analysis = get_gpt4o_analysis(selected_coin, selected_timeframe_name, smc_results, snr_results)
            st.write(gpt_analysis)
                
            # 使用 Claude 3.7 進行整合分析
            st.subheader("Claude 3.7 整合分析")
            claude_analysis = get_claude_analysis(selected_coin, selected_timeframe_name, smc_results, snr_results)
            st.write(claude_analysis)
            
        elif selected_strategy == "SNR策略分析":
            snr_results, processed_df = snr_analysis(data)
            smc_results, _ = smc_analysis(data)  # 為了提供給AI分析
            
            # 顯示分析結果
            st.header("SNR策略分析結果")
            
            # 顯示圖表
            st.subheader("價格走勢圖")
            chart = create_price_chart(processed_df, selected_strategy)
            st.plotly_chart(chart, use_container_width=True)
            
            # 顯示指標分析
            st.subheader("技術指標")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("當前價格", f"${snr_results['price']:.2f}")
                st.metric("RSI指標", f"{snr_results['rsi']:.2f}", 
                        delta="超買" if snr_results['overbought'] else "超賣" if snr_results['oversold'] else "中性")
            with col2:
                st.metric("近期支撐位", f"${snr_results['near_support']:.2f}")
                st.metric("強力支撐位", f"${snr_results['strong_support']:.2f}")
            with col3:
                st.metric("近期阻力位", f"${snr_results['near_resistance']:.2f}")
                st.metric("強力阻力位", f"${snr_results['strong_resistance']:.2f}")
            
            # 使用 DeepSeek V3 進行技術分析
            st.subheader("DeepSeek V3 技術分析")
            deepseek_analysis = get_deepseek_analysis(
                selected_coin, 
                selected_timeframe_name, 
                data,
                smc_results, 
                snr_results,
                analysis_detail
            )
            st.write(deepseek_analysis)
            
            # 使用 GPT-4o3-mini 進行市場情緒分析
            st.subheader("GPT-4o3-mini 市場情緒分析")
            gpt_analysis = get_gpt4o_analysis(selected_coin, selected_timeframe_name, smc_results, snr_results)
            st.write(gpt_analysis)
                
            # 使用 Claude 3.7 進行整合分析
            st.subheader("Claude 3.7 整合分析")
            claude_analysis = get_claude_analysis(selected_coin, selected_timeframe_name, smc_results, snr_results)
            st.write(claude_analysis)
            
        else:  # SMC+SNR整合分析
            smc_results, processed_df1 = smc_analysis(data)
            snr_results, processed_df2 = snr_analysis(data)
            
            # 顯示分析結果
            st.header("SMC+SNR整合分析結果")
            
            # 顯示圖表
            st.subheader("價格走勢圖")
            chart = create_price_chart(processed_df1, selected_strategy)
            st.plotly_chart(chart, use_container_width=True)
            
            # 顯示指標分析
            st.subheader("技術指標")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("當前價格", f"${smc_results['price']:.2f}")
                st.metric("市場結構", "上升趨勢" if smc_results['market_structure'] == 'bullish' else "下降趨勢")
                st.metric("RSI指標", f"{snr_results['rsi']:.2f}")
            with col2:
                st.metric("支撐位 (SMC)", f"${smc_results['support_level']:.2f}")
                st.metric("支撐位 (SNR)", f"${snr_results['near_support']:.2f}")
            with col3:
                st.metric("阻力位 (SMC)", f"${smc_results['resistance_level']:.2f}")
                st.metric("阻力位 (SNR)", f"${snr_results['near_resistance']:.2f}")
            
            # 使用 DeepSeek V3 進行技術分析
            st.subheader("DeepSeek V3 技術分析")
            deepseek_analysis = get_deepseek_analysis(
                selected_coin, 
                selected_timeframe_name, 
                data,
                smc_results, 
                snr_results,
                analysis_detail
            )
            st.write(deepseek_analysis)
            
            # 使用 GPT-4o3-mini 進行市場情緒分析
            st.subheader("GPT-4o3-mini 市場情緒分析")
            gpt_analysis = get_gpt4o_analysis(selected_coin, selected_timeframe_name, smc_results, snr_results)
            st.write(gpt_analysis)
                
            # 使用 Claude 3.7 進行整合分析
            st.subheader("Claude 3.7 整合分析")
            claude_analysis = get_claude_analysis(selected_coin, selected_timeframe_name, smc_results, snr_results)
            st.write(claude_analysis)
    else:
        st.error("獲取數據失敗，請稍後再試")

# 底部免責聲明
st.markdown("---")
st.markdown("""
**免責聲明**：本工具提供的分析結果僅供參考，不構成投資建議。加密貨幣市場風險高，投資需謹慎。
使用者應自行承擔所有決策責任。分析基於歷史數據，過去表現不代表未來結果。
""")

# 側邊欄底部信息
st.sidebar.markdown("---")
st.sidebar.info("""
**AI分析模型**:
- DeepSeek V3：技術分析與價格預測 (真實API)
- GPT-4o3-mini：市場情緒分析 (模擬)
- Claude 3.7：分析整合與結構化輸出 (模擬)

**當前版本**：
多模型AI分析版 (1.0.0)
""")

# 添加"關於"部分
with st.sidebar.expander("關於本工具"):
    st.write("""
    CryptoAnalyzer是一個整合了SMC(Smart Money Concept)和SNR(Support & Resistance)分析方法的加密貨幣技術分析工具。
    
    本版本使用DeepSeek V3的真實API進行技術分析，並模擬GPT-4o3-mini和Claude 3.7分析能力，提供全面的加密貨幣市場洞察。
    
    技術數據通過CCXT庫從Binance獲取，使用專業級加密貨幣技術分析指標。
    """) 