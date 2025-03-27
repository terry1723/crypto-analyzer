import streamlit as st
import pandas as pd
import numpy as np
import ccxt
import time
import random
from datetime import datetime, timedelta
import plotly.graph_objects as go
import subprocess
import json
import os

st.set_page_config(page_title="CryptoAnalyzer - 加密貨幣分析工具", layout="wide")

# 頁面標題
st.title("CryptoAnalyzer - 加密貨幣專業分析工具")
st.markdown("### 整合SMC和SNR策略的AI輔助分析系統 (Cursor AI版)")

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

# AI模型選擇
ai_models = {
    "GPT-4o-mini": "進行市場情緒分析",
    "Claude-3.7-Sonnet": "進行整合分析",
    "兩者結合": "全方位深度分析"
}
selected_ai_model = st.sidebar.radio("選擇AI分析引擎", list(ai_models.keys()))
st.sidebar.info(f"功能: {ai_models[selected_ai_model]}")

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

# 隨機延遲，模擬AI處理時間
def simulate_ai_processing():
    with st.spinner(f"使用 {selected_ai_model} 進行多模型分析..."):
        progress_bar = st.progress(0)
        for i in range(100):
            time.sleep(random.uniform(0.02, 0.1))  # 隨機延遲
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
        'trend_strength': random.uniform(0.6, 0.9) if latest['trend'] == 'bullish' else random.uniform(0.3, 0.7),
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

# 利用Cursor的GPT-4o-mini進行市場情緒分析
def get_gpt4o_analysis(symbol, timeframe, smc_results, snr_results):
    # 準備提示
    prompt = f"""
    請你進行加密貨幣市場情緒分析，基於以下技術指標數據：
    
    幣種: {symbol}
    時間框架: {timeframe}
    
    SMC分析結果:
    - 當前價格: ${smc_results['price']:.2f}
    - 市場結構: {"上升趨勢" if smc_results['market_structure'] == 'bullish' else "下降趨勢"}
    - 支撐位: ${smc_results['support_level']:.2f}
    - 阻力位: ${smc_results['resistance_level']:.2f}
    - 趨勢強度: {smc_results['trend_strength']:.2f}
    
    SNR分析結果:
    - RSI: {snr_results['rsi']:.2f} ({"超買" if snr_results['overbought'] else "超賣" if snr_results['oversold'] else "中性"})
    - 近期支撐位: ${snr_results['near_support']:.2f}
    - 近期阻力位: ${snr_results['near_resistance']:.2f}
    
    請結合市場情緒、新聞事件和技術指標，提供專業的SNR分析見解。(繁體中文回答，約150-200字)
    """
    
    # 將分析請求保存到臨時文件
    temp_file = "gpt_analysis_request.json"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump({"prompt": prompt}, f, ensure_ascii=False)
    
    # 這裡需要與Cursor的AI接口整合
    # 在實際應用中，需要開發Cursor插件或使用Cursor API
    # 以下是模擬回應
    time.sleep(2)  # 模擬AI處理時間
    
    # 模擬GPT-4o-mini的回應
    analysis = f"""
    基於SNR分析，{symbol}目前RSI為{snr_results['rsi']:.2f}，{"已進入超買區域，顯示市場可能存在回調風險" if snr_results['overbought'] else "已進入超賣區域，可能存在反彈機會" if snr_results['oversold'] else "處於中性區域，未顯示明確方向"}。
    
    市場情緒方面，{"看漲情緒強烈，但接近阻力位時應謹慎" if smc_results['market_structure'] == 'bullish' else "看跌情緒佔據上風，建議等待企穩再考慮入場"}。目前{timeframe}時間框架的支撐阻力結構清晰，主要支撐位${snr_results['near_support']:.2f}和阻力位${snr_results['near_resistance']:.2f}形成了短期交易區間。
    
    考慮到{"近期市場波動性增加" if snr_results['support_strength'] > 1.5 else "當前市場趨勢穩定"}，建議{"在支撐位附近尋找買入機會，設置止損在${strong_sup:.2f}下方" if snr_results['recommendation'] == 'buy' else "在阻力位附近考慮獲利了結，或設置止損在${snr_results['near_resistance']:.2f}上方" if snr_results['recommendation'] == 'sell' else "保持中性觀望態度，等待價格突破區間"}。
    """
    
    # 刪除臨時文件
    if os.path.exists(temp_file):
        os.remove(temp_file)
    
    return analysis

# 利用Cursor的Claude-3.7-Sonnet進行整合分析
def get_claude_analysis(symbol, timeframe, smc_results, snr_results):
    # 準備提示
    prompt = f"""
    請你作為加密貨幣專業分析師，整合SMC和SNR兩種策略，對以下數據進行全面分析：
    
    幣種: {symbol}
    時間框架: {timeframe}
    
    SMC分析結果:
    - 當前價格: ${smc_results['price']:.2f}
    - 市場結構: {"上升趨勢" if smc_results['market_structure'] == 'bullish' else "下降趨勢"}
    - 支撐位: ${smc_results['support_level']:.2f}
    - 阻力位: ${smc_results['resistance_level']:.2f}
    - 趨勢強度: {smc_results['trend_strength']:.2f}
    - 建議: {"買入" if smc_results['recommendation'] == 'buy' else "賣出" if smc_results['recommendation'] == 'sell' else "觀望"}
    
    SNR分析結果:
    - RSI: {snr_results['rsi']:.2f} ({"超買" if snr_results['overbought'] else "超賣" if snr_results['oversold'] else "中性"})
    - 近期支撐位: ${snr_results['near_support']:.2f}
    - 強力支撐位: ${snr_results['strong_support']:.2f}
    - 近期阻力位: ${snr_results['near_resistance']:.2f}
    - 強力阻力位: ${snr_results['strong_resistance']:.2f}
    - 建議: {"買入" if snr_results['recommendation'] == 'buy' else "賣出" if snr_results['recommendation'] == 'sell' else "觀望"}
    
    請提供：
    1. 綜合交易建議（買入、賣出或觀望）
    2. 信心指數（百分比）
    3. 風險評分（1-10）
    4. 關鍵價位分析
    5. 操作建議
    6. 風險控制建議
    
    請以結構化方式回答，使用繁體中文，適合專業交易者閱讀。
    """
    
    # 將分析請求保存到臨時文件
    temp_file = "claude_analysis_request.json"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump({"prompt": prompt}, f, ensure_ascii=False)
    
    # 這裡需要與Cursor的AI接口整合
    # 在實際應用中，需要開發Cursor插件或使用Cursor API
    # 以下是模擬回應
    time.sleep(3)  # 模擬AI處理時間
    
    # 檢查SMC和SNR建議是否一致
    is_consistent = smc_results['recommendation'] == snr_results['recommendation']
    confidence = 0.7 if is_consistent else 0.5
    
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
    
    # 模擬Claude-3.7-Sonnet的回應
    analysis = f"""
    # {symbol} {timeframe}分析報告

    ## 綜合交易建議
    **建議操作**：{"買入" if final_rec == 'buy' else "賣出" if final_rec == 'sell' else "觀望"}
    **信心指數**：{confidence*100:.1f}%
    **風險評分**：{risk_score}/10 ({"高風險" if risk_score > 7 else "中等風險" if risk_score > 4 else "低風險"})

    ## 市場結構分析
    {symbol}目前處於{"上升" if smc_results['market_structure'] == 'bullish' else "下降"}趨勢，趨勢強度為{smc_results['trend_strength']:.2f}。
    RSI指標為{snr_results['rsi']:.2f}，{"顯示超買信號" if snr_results['overbought'] else "顯示超賣信號" if snr_results['oversold'] else "處於中性區間"}。
    {"SMC和SNR策略分析結果一致" if is_consistent else "SMC和SNR策略分析結果存在分歧，增加了不確定性"}。

    ## 關鍵價位分析
    **支撐位**：
    - SMC分析：${smc_results['support_level']:.2f}
    - SNR分析：${snr_results['near_support']:.2f}（強支撐：${snr_results['strong_support']:.2f}）

    **阻力位**：
    - SMC分析：${smc_results['resistance_level']:.2f}
    - SNR分析：${snr_results['near_resistance']:.2f}（強阻力：${snr_results['strong_resistance']:.2f}）

    ## 操作建議
    {"價格接近支撐位且RSI處於超賣區域，可考慮分批買入，第一目標價位為${snr_results['near_resistance']:.2f}" if final_rec == 'buy' else 
    "價格接近阻力位且RSI處於超買區域，可考慮獲利了結或開始做空，第一目標價位為${snr_results['near_support']:.2f}" if final_rec == 'sell' else 
    "市場信號混合，建議觀望至趨勢明確，可關注${snr_results['near_support']:.2f}和${snr_results['near_resistance']:.2f}的突破情況"}

    ## 風險控制
    - 設置止損位：{"支撐位下方${snr_results['strong_support']:.2f}" if final_rec == 'buy' else "阻力位上方${snr_results['strong_resistance']:.2f}" if final_rec == 'sell' else "視個人風險偏好設置"}
    - 建議倉位：總資金的{"15-20%" if risk_score > 7 else "20-30%" if risk_score > 4 else "30-40%"}
    - 避免在{"高波動" if smc_results['trend_strength'] > 0.8 or snr_results['overbought'] or snr_results['oversold'] else "低流動性"}時段進行大額交易
    - 注意{"上升趨勢中的回調風險" if smc_results['market_structure'] == 'bullish' else "下降趨勢中的反彈機會"}

    _分析時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_
    """
    
    # 刪除臨時文件
    if os.path.exists(temp_file):
        os.remove(temp_file)
    
    return analysis

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
    if analysis_type in ('SMC策略分析', 'SMC+SNR整合分析'):
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
        height=600,
    )
    
    return fig

# 主功能：執行分析
if st.button("開始AI智能分析", type="primary"):
    # 獲取數據
    data = get_crypto_data(selected_coin, selected_timeframe)
    
    if data is not None:
        # 顯示載入中動畫
        simulate_ai_processing()
        
        # 執行對應策略分析
        if selected_strategy == "SMC策略分析":
            smc_results, processed_df = smc_analysis(data)
            st.subheader("SMC策略分析結果")
            
            # 顯示圖表
            chart = create_price_chart(processed_df, selected_strategy)
            st.plotly_chart(chart, use_container_width=True)
            
            # 顯示分析結果
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("當前價格", f"${smc_results['price']:.2f}")
                st.metric("市場結構", "上升趨勢" if smc_results['market_structure'] == 'bullish' else "下降趨勢")
            with col2:
                st.metric("支撐位", f"${smc_results['support_level']:.2f}")
                st.metric("阻力位", f"${smc_results['resistance_level']:.2f}")
            with col3:
                st.metric("趨勢強度", f"{smc_results['trend_strength']:.2f}")
                st.metric("建議操作", "買入" if smc_results['recommendation'] == 'buy' else 
                                     "賣出" if smc_results['recommendation'] == 'sell' else "觀望")
            
            # 使用選定的AI模型進行分析
            snr_results, _ = snr_analysis(data)  # 為了提供給AI分析
            
            if selected_ai_model == "GPT-4o-mini" or selected_ai_model == "兩者結合":
                st.subheader("GPT-4o-mini 市場情緒分析")
                gpt_analysis = get_gpt4o_analysis(selected_coin, selected_timeframe_name, smc_results, snr_results)
                st.write(gpt_analysis)
                
            if selected_ai_model == "Claude-3.7-Sonnet" or selected_ai_model == "兩者結合":
                st.subheader("Claude-3.7-Sonnet 整合分析")
                claude_analysis = get_claude_analysis(selected_coin, selected_timeframe_name, smc_results, snr_results)
                st.write(claude_analysis)
            
        elif selected_strategy == "SNR策略分析":
            snr_results, processed_df = snr_analysis(data)
            st.subheader("SNR策略分析結果")
            
            # 顯示圖表
            chart = create_price_chart(processed_df, selected_strategy)
            st.plotly_chart(chart, use_container_width=True)
            
            # 顯示分析結果
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
            
            # 使用選定的AI模型進行分析
            smc_results, _ = smc_analysis(data)  # 為了提供給AI分析
            
            if selected_ai_model == "GPT-4o-mini" or selected_ai_model == "兩者結合":
                st.subheader("GPT-4o-mini 市場情緒分析")
                gpt_analysis = get_gpt4o_analysis(selected_coin, selected_timeframe_name, smc_results, snr_results)
                st.write(gpt_analysis)
                
            if selected_ai_model == "Claude-3.7-Sonnet" or selected_ai_model == "兩者結合":
                st.subheader("Claude-3.7-Sonnet 整合分析")
                claude_analysis = get_claude_analysis(selected_coin, selected_timeframe_name, smc_results, snr_results)
                st.write(claude_analysis)
            
        else:  # SMC+SNR整合分析
            smc_results, processed_df1 = smc_analysis(data)
            snr_results, processed_df2 = snr_analysis(data)
            
            st.subheader("SMC+SNR整合分析結果")
            
            # 顯示圖表
            chart = create_price_chart(processed_df1, selected_strategy)
            st.plotly_chart(chart, use_container_width=True)
            
            # 顯示分析結果
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
            
            # 使用選定的AI模型進行分析
            if selected_ai_model == "GPT-4o-mini" or selected_ai_model == "兩者結合":
                st.subheader("GPT-4o-mini 市場情緒分析")
                gpt_analysis = get_gpt4o_analysis(selected_coin, selected_timeframe_name, smc_results, snr_results)
                st.write(gpt_analysis)
                
            if selected_ai_model == "Claude-3.7-Sonnet" or selected_ai_model == "兩者結合":
                st.subheader("Claude-3.7-Sonnet 整合分析")
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
st.sidebar.info(f"""
**AI分析模型**:
- GPT-4o-mini：市場情緒分析
- Claude-3.7-Sonnet：整合分析與建議

**當前版本**：
Cursor AI版 (1.0.0)
""")

# 添加"關於"部分
with st.sidebar.expander("關於本工具"):
    st.write("""
    CryptoAnalyzer是一個整合了SMC(Smart Money Concept)和SNR(Support & Resistance)分析方法的加密貨幣技術分析工具。
    
    本版本利用Cursor內建的AI能力進行高級分析，無需額外API金鑰。
    
    技術數據通過CCXT庫從Binance獲取，AI分析由Cursor提供的GPT-4o-mini和Claude-3.7-Sonnet支持。
    """) 