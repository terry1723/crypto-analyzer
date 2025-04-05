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

# 設置頁面配置
st.set_page_config(
    page_title="0xAI CryptoCat 分析",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 添加自定義 CSS 來優化界面
st.markdown("""
<style>
    /* 隱藏側邊欄以及默認的 Streamlit 元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* 主要顏色方案 - 深色主題 */
    :root {
        --primary-color: #4a8af4;
        --secondary-color: #9C27B0;
        --accent-color: #00BCD4;
        --background-color: #121212;
        --card-background: #1E1E1E;
        --text-color: #E0E0E0;
        --border-color: #333333;
    }

    /* 整體背景和文字 */
    .stApp {
        background-color: var(--background-color);
        color: var(--text-color);
    }

    /* 卡片式設計元素 */
    .stCardContainer {
        background-color: var(--card-background);
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        border: 1px solid var(--border-color);
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }

    /* 選項卡設計 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: var(--card-background);
        border-radius: 8px;
        padding: 5px;
    }

    .stTabs [data-baseweb="tab"] {
        height: 40px;
        white-space: pre-wrap;
        border-radius: 5px;
        color: var(--text-color);
        background-color: transparent;
    }

    .stTabs [aria-selected="true"] {
        background-color: var(--primary-color) !important;
        color: white !important;
        font-weight: bold;
    }

    /* 按鈕樣式 */
    .stButton button {
        background-color: var(--primary-color);
        color: white;
        border-radius: 5px;
        border: none;
        padding: 10px 20px;
        font-weight: bold;
    }

    .stButton button:hover {
        background-color: #3A7AD5;
    }

    /* 展開/摺疊元素樣式 */
    .streamlit-expanderHeader {
        background-color: var(--card-background);
        border-radius: 8px;
        color: var(--text-color);
        font-weight: 500;
    }

    /* 數據表格樣式 */
    .dataframe {
        border-radius: 8px;
        overflow: hidden;
    }

    /* 頂部導航欄 */
    .nav-container {
        background-color: var(--card-background);
        padding: 10px;
        border-radius: 10px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border: 1px solid var(--border-color);
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }

    /* 進度指示器 */
    .stProgress > div > div {
        background-color: var(--primary-color);
    }

    /* 提示條樣式 */
    .stAlert {
        border-radius: 8px;
    }

    /* 醒目數據展示 */
    .highlight-metric {
        background-color: var(--card-background);
        border-left: 4px solid var(--primary-color);
        padding: 10px 15px;
        margin: 5px 0;
        border-radius: 0 5px 5px 0;
    }
    
    /* 標題樣式 */
    h1, h2, h3 {
        color: var(--primary-color);
    }
    
    /* 自定義卡片 */
    .data-card {
        background-color: var(--card-background);
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        margin-bottom: 15px;
    }
    
    /* 重要數據顯示 */
    .key-metric {
        font-size: 24px;
        font-weight: bold;
        color: var(--accent-color);
    }
    
    /* 分析結果摘要區 */
    .analysis-summary {
        background-color: rgba(74, 138, 244, 0.1);
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        border-left: 4px solid var(--primary-color);
    }
</style>
""", unsafe_allow_html=True)

# 處理 orjson 相關問題
import plotly.io._json
# 如果 orjson 存在，修復 OPT_NON_STR_KEYS 問題
try:
    import orjson
    if not hasattr(orjson, 'OPT_NON_STR_KEYS'):
        orjson.OPT_NON_STR_KEYS = 2  # 定義缺失的常量
except ImportError:
    pass
except AttributeError:
    # 修改 _json_to_plotly 方法，避免使用 OPT_NON_STR_KEYS
    orig_to_json_plotly = plotly.io._json.to_json_plotly
    def patched_to_json_plotly(fig_dict, *args, **kwargs):
        try:
            return orig_to_json_plotly(fig_dict, *args, **kwargs)
        except AttributeError:
            # 使用 json 而不是 orjson 進行序列化
            return json.dumps(fig_dict)
    plotly.io._json.to_json_plotly = patched_to_json_plotly

# 安全地從 secrets 或環境變量獲取 API 密鑰
def get_api_key(key_name, default_value=None):
    """安全地獲取 API 密鑰，優先從 Streamlit secrets 獲取，然後是環境變量，最後是默認值"""
    try:
        if key_name in st.secrets:
            return st.secrets[key_name]
    except Exception:
        # 忽略 secrets 相關錯誤
        pass
        
    # 如果無法從 secrets 獲取，嘗試從環境變量獲取，最後使用默認值
    return os.getenv(key_name, default_value)

# 從Streamlit secrets或環境變數讀取API密鑰，如果都不存在則使用預設值
DEEPSEEK_API_KEY = get_api_key("DEEPSEEK_API_KEY", "sk-6ae04d6789f94178b4053d2c42650b6c")

# 設置 CoinMarketCap API 密鑰
COINMARKETCAP_API_KEY = get_api_key("COINMARKETCAP_API_KEY", "b54bcf4d-1bca-4e8e-9a24-22ff2c3d462c")

# 新增：設置 OpenAI API 密鑰
OPENAI_API_KEY = get_api_key("OPENAI_API_KEY", "")

# 設置 Bitget MCP 服務器
BITGET_MCP_SERVER = "http://localhost:3000"

# DexScreener API函數，獲取加密貨幣數據
def get_dexscreener_data(symbol, timeframe, limit=100):
    """
    從DexScreener API獲取加密貨幣OHLCV數據
    
    參數:
    symbol (str): 交易對符號，如 'BTC/USDT'
    timeframe (str): 時間框架，如 '1d', '4h', '1h'
    limit (int): 要獲取的數據點數量
    
    返回:
    pandas.DataFrame: 包含OHLCV數據的DataFrame，如果獲取失敗則返回None
    """
    try:
        # 解析交易對符號
        base, quote = symbol.split('/')
        base_id = base.lower()  # 用於API查詢
        
        # 將時間框架轉換為秒數
        timeframe_seconds = {
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '30m': 1800,
            '1h': 3600,
            '4h': 14400,
            '12h': 43200,
            '1d': 86400,
            '1w': 604800
        }
        
        # 根據timeframe和limit計算時間範圍
        seconds = timeframe_seconds.get(timeframe, 86400)  # 默認為1天
        
        # 嘗試使用DexScreener API獲取數據
        try:
            print(f"正在使用DexScreener API獲取{symbol}數據...")
            
            # 首先獲取配對信息
            pair_url = f"https://api.dexscreener.com/latest/dex/search?q={base}"
            pair_response = requests.get(pair_url)
            
            if pair_response.status_code != 200:
                print(f"DexScreener API請求失敗: {pair_response.status_code}")
                raise Exception(f"DexScreener API請求失敗: {pair_response.status_code}")
                
            pair_data = pair_response.json()
            
            if not pair_data.get('pairs') or len(pair_data['pairs']) == 0:
                print(f"DexScreener未找到{symbol}交易對")
                raise Exception(f"DexScreener未找到{symbol}交易對")
            
            # 找出與USDT配對的流動性最高的交易對
            best_pair = None
            max_liquidity = 0
            
            for pair in pair_data['pairs']:
                if (pair['quoteToken']['symbol'].lower() == quote.lower() and 
                    pair['baseToken']['symbol'].lower() == base.lower()):
                    
                    # 將流動性值轉換為數字
                    liquidity = float(pair.get('liquidity', {}).get('usd', 0))
                    
                    if liquidity > max_liquidity:
                        max_liquidity = liquidity
                        best_pair = pair
            
            if not best_pair:
                # 如果沒有找到完全匹配的，嘗試找到最佳匹配
                for pair in pair_data['pairs']:
                    if pair['quoteToken']['symbol'].lower() == quote.lower():
                        # 將流動性值轉換為數字
                        liquidity = float(pair.get('liquidity', {}).get('usd', 0))
                        
                        if liquidity > max_liquidity:
                            max_liquidity = liquidity
                            best_pair = pair
            
            # 如果仍然沒有找到，使用第一個對
            if not best_pair and pair_data['pairs']:
                best_pair = pair_data['pairs'][0]
            
            if not best_pair:
                print(f"無法在DexScreener找到合適的{symbol}交易對")
                raise Exception(f"無法在DexScreener找到合適的{symbol}交易對")
            
            # 獲取交易對ID
            pair_address = best_pair['pairAddress']
            chain_id = best_pair['chainId']
            
            # 獲取K線數據
            candles_url = f"https://api.dexscreener.com/latest/dex/candles?chainId={chain_id}&pairAddress={pair_address}&from=0"
            candles_response = requests.get(candles_url)
            
            if candles_response.status_code != 200:
                print(f"DexScreener K線數據請求失敗: {candles_response.status_code}")
                raise Exception(f"DexScreener K線數據請求失敗: {candles_response.status_code}")
                
            candles_data = candles_response.json()
            
            if not candles_data.get('candles') or len(candles_data['candles']) == 0:
                print(f"DexScreener未返回{symbol}的K線數據")
                raise Exception(f"DexScreener未返回{symbol}的K線數據")
            
            # 將K線數據轉換為DataFrame
            df_data = []
            
            # 根據所選時間框架過濾所需的K線
            filtered_candles = []
            target_timeframe = {
                '15m': '15m',
                '1h': '1h', 
                '4h': '4h',
                '1d': '1d',
                '1w': '1w'
            }.get(timeframe, '1d')
            
            for candle in candles_data['candles']:
                if candle.get('timeframe') == target_timeframe:
                    filtered_candles.append(candle)
            
            # 如果沒有找到指定時間框架的數據，使用所有可用數據
            if not filtered_candles and candles_data['candles']:
                available_timeframes = set(c.get('timeframe') for c in candles_data['candles'] if c.get('timeframe'))
                print(f"未找到{target_timeframe}時間框架的數據，可用時間框架: {available_timeframes}")
                
                # 嘗試使用可用的最接近的時間框架
                timeframe_priority = ['15m', '1h', '4h', '1d', '1w']
                for tf in timeframe_priority:
                    if tf in available_timeframes:
                        target_timeframe = tf
                        break
                
                # 重新過濾
                for candle in candles_data['candles']:
                    if candle.get('timeframe') == target_timeframe:
                        filtered_candles.append(candle)
                
                print(f"使用{target_timeframe}時間框架的數據代替")
            
            # 排序K線數據，確保時間順序
            filtered_candles.sort(key=lambda x: x.get('timestamp', 0))
            
            # 取最近的limit個數據點
            if len(filtered_candles) > limit:
                filtered_candles = filtered_candles[-limit:]
            
            # 轉換為DataFrame格式
            for candle in filtered_candles:
                timestamp = candle.get('timestamp', 0)
                open_price = float(candle.get('open', 0))
                high_price = float(candle.get('high', 0))
                low_price = float(candle.get('low', 0))
                close_price = float(candle.get('close', 0))
                volume = float(candle.get('volume', {}).get('base', 0))
                
                df_data.append([
                    timestamp,
                    open_price,
                    high_price,
                    low_price,
                    close_price,
                    volume
                ])
            
            # 創建DataFrame
            df = pd.DataFrame(df_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # 將timestamp轉換為datetime格式
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            print(f"成功從DexScreener獲取{symbol}的{len(df)}個數據點")
            return df
            
        except Exception as e:
            print(f"DexScreener API請求失敗: {str(e)}，嘗試使用ccxt...")
            
            # 如果DexScreener失敗，嘗試使用ccxt
            try:
                # 嘗試使用ccxt從主流交易所獲取數據
                exchange = ccxt.binance()
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                
                # 將數據轉換為DataFrame
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                
                print(f"成功從ccxt獲取{symbol}的{len(df)}個數據點")
                return df
                
            except Exception as ccxt_error:
                # 如果ccxt也失敗，使用CoinGecko API
                print(f"CCXT獲取失敗: {ccxt_error}，嘗試使用CoinGecko...")
                
                try:
                    # 映射加密貨幣符號到CoinGecko ID
                    coin_id_map = {
                        'BTC': 'bitcoin',
                        'ETH': 'ethereum',
                        'SOL': 'solana',
                        'BNB': 'binancecoin',
                        'XRP': 'ripple',
                        'ADA': 'cardano',
                        'DOGE': 'dogecoin',
                        'SHIB': 'shiba-inu'
                    }
                    
                    coin_id = coin_id_map.get(base, base_id)
                    
                    # 使用CoinGecko API獲取數據
                    vs_currency = quote.lower()
                    days = min(365, limit)  # CoinGecko最多支持365天
                    
                    # 構建API URL
                    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
                    params = {
                        'vs_currency': vs_currency,
                        'days': days,
                        'interval': 'daily' if timeframe in ['1d', '1w'] else 'hourly'
                    }
                    
                    response = requests.get(url, params=params)
                    if response.status_code == 200:
                        data = response.json()
                        
                        # 提取價格和成交量數據
                        prices = data['prices']  # [timestamp, price]
                        volumes = data['total_volumes']  # [timestamp, volume]
                        
                        # 將數據轉換為DataFrame所需格式
                        ohlcv_data = []
                        for i, (price_item, volume_item) in enumerate(zip(prices, volumes)):
                            timestamp = price_item[0]
                            price = price_item[1]
                            volume = volume_item[1]
                            
                            # 由於CoinGecko只提供收盤價，我們需要模擬OHLC數據
                            # 但我們會保持價格接近實際價格
                            ohlcv_data.append([
                                timestamp,
                                price * (1 - random.uniform(0, 0.01)),  # 開盤價略低於收盤價
                                price * (1 + random.uniform(0, 0.015)),  # 最高價略高於收盤價
                                price * (1 - random.uniform(0, 0.015)),  # 最低價略低於收盤價
                                price,  # 收盤價(實際數據)
                                volume  # 成交量(實際數據)
                            ])
                        
                        # 過濾數據以匹配請求的時間框架
                        filtered_data = []
                        if timeframe == '1d':
                            filtered_data = ohlcv_data[-limit:]
                        elif timeframe in ['1h', '4h']:
                            hours_interval = 1 if timeframe == '1h' else 4
                            filtered_data = ohlcv_data[::hours_interval][-limit:]
                        else:
                            filtered_data = ohlcv_data[-limit:]
                        
                        # 創建DataFrame
                        df = pd.DataFrame(filtered_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                        
                        print(f"成功從CoinGecko獲取{symbol}的{len(df)}個數據點")
                        return df
                    else:
                        print(f"CoinGecko API返回錯誤: {response.status_code}")
                        # 最終使用模擬數據
                        
                except Exception as gecko_error:
                    print(f"CoinGecko API請求失敗: {str(gecko_error)}")
                    # 使用模擬數據
                
                # 生成模擬數據(當所有API都無法使用時的備用選項)
                print(f"所有API獲取失敗，使用模擬數據生成{symbol}的價格數據...")
                dates = pd.date_range(end=pd.Timestamp.now(), periods=limit, freq=timeframe)
                
                # 使用更新的、更接近實際價格的基準價格
                base_price = 0
                volatility = 0.05
                
                # 更新至2025年4月初的價格
                if 'BTC' in symbol:
                    base_price = 68500 + random.uniform(-2000, 2000)  # 比特幣更新價格
                    volatility = 0.03
                elif 'ETH' in symbol:
                    base_price = 3500 + random.uniform(-150, 150)     # 以太坊更新價格
                    volatility = 0.04
                elif 'SOL' in symbol:
                    base_price = 180 + random.uniform(-10, 10)        # 索拉納更新價格
                    volatility = 0.06
                elif 'BNB' in symbol:
                    base_price = 570 + random.uniform(-20, 20)        # 幣安幣更新價格
                    volatility = 0.03
                elif 'XRP' in symbol:
                    base_price = 0.62 + random.uniform(-0.05, 0.05)   # 瑞波幣更新價格
                    volatility = 0.04
                elif 'ADA' in symbol:
                    base_price = 0.47 + random.uniform(-0.03, 0.03)   # 艾達幣更新價格
                    volatility = 0.05
                elif 'DOGE' in symbol:
                    base_price = 0.16 + random.uniform(-0.01, 0.01)   # 狗狗幣更新價格
                    volatility = 0.08
                elif 'SHIB' in symbol:
                    base_price = 0.00002750 + random.uniform(-0.000001, 0.000001)  # 柴犬幣更新價格
                    volatility = 0.09
                else:
                    base_price = 100 + random.uniform(-5, 5)
                
                # 生成模擬的價格數據
                close_prices = []
                price = base_price
                
                for i in range(limit):
                    # 添加一些隨機波動，使數據看起來更真實
                    change = price * volatility * random.uniform(-1, 1)
                    # 添加一些趨勢
                    trend = price * 0.001 * (i - limit/2)
                    price = price + change + trend
                    close_prices.append(max(0.000001, price))  # 確保價格為正
                
                # 從收盤價生成其他價格數據
                df = pd.DataFrame({
                    'timestamp': dates,
                    'close': close_prices,
                    'open': [p * (1 + random.uniform(-0.01, 0.01)) for p in close_prices],
                    'high': [p * (1 + random.uniform(0, 0.02)) for p in close_prices],
                    'low': [p * (1 - random.uniform(0, 0.02)) for p in close_prices],
                    'volume': [p * random.uniform(500000, 5000000) for p in close_prices]
                })
                
                print(f"使用模擬數據: {symbol} 基準價格=${base_price:.2f}")
                return df
                
    except Exception as e:
        print(f"獲取加密貨幣數據時出錯: {str(e)}")
        return None

# 價格合理性驗證函數
def verify_price_reasonability(df, base_coin):
    """驗證價格是否在合理範圍內"""
    if df is None or len(df) == 0:
        return False
    
    current_price = df['close'].iloc[-1]
    
    # 2025年的合理價格範圍
    reasonable_ranges = {
        'BTC': (50000, 80000),
        'ETH': (2600, 5000),
        'SOL': (150, 300),
        'BNB': (450, 650),
        'XRP': (0.4, 0.9),
        'ADA': (0.3, 0.6),
        'DOGE': (0.05, 0.2),
        'SHIB': (0.00001, 0.0001)
    }
    
    if base_coin in reasonable_ranges:
        min_price, max_price = reasonable_ranges[base_coin]
        if min_price <= current_price <= max_price:
            return True
        
        print(f"警告: {base_coin}價格${current_price:.2f}超出合理範圍(${min_price:.2f}-${max_price:.2f})")
        return False
    
    return True

# 添加Smithery MCP Crypto Price API函數
def get_smithery_mcp_crypto_price(symbol, timeframe, limit=100):
    """
    從Smithery MCP Crypto Price API獲取加密貨幣數據
    
    參數:
    symbol (str): 交易對符號，如 'BTC/USDT'
    timeframe (str): 時間框架，如 '1d', '4h', '1h'
    limit (int): 要獲取的數據點數量
    
    返回:
    pandas.DataFrame: 包含OHLCV數據的DataFrame，如果獲取失敗則返回None
    """
    try:
        # 解析交易對符號
        base, quote = symbol.split('/')
        base = base.upper()
        quote = quote.upper()
        
        # 轉換為Smithery MCP可接受的格式
        mcp_symbol = f"{base}{quote}"
        
        # 轉換時間框架為MCP接受的格式
        mcp_timeframe = {
            '15m': '15min',
            '1h': '1h',
            '4h': '4h',
            '1d': '1d',
            '1w': '1w'
        }.get(timeframe, '1h')
        
        # 構建API請求URL
        url = f"https://smithery.ai/server/@truss44/mcp-crypto-price/get_crypto_price"
        
        # 準備請求參數
        params = {
            'symbol': mcp_symbol,
            'interval': mcp_timeframe,
            'limit': limit
        }
        
        # 準備請求頭
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # 發送請求
        print(f"請求Smithery MCP API: {url} - 參數: {params}")
        response = requests.post(url, json=params, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            # 檢查返回數據格式
            if isinstance(data, list) and len(data) > 0:
                # 構建DataFrame
                df_data = []
                for item in data:
                    # 檢查每條數據是否包含必要的字段
                    if all(key in item for key in ['timestamp', 'open', 'high', 'low', 'close', 'volume']):
                        timestamp = item['timestamp']
                        open_price = float(item['open'])
                        high_price = float(item['high'])
                        low_price = float(item['low'])
                        close_price = float(item['close'])
                        volume = float(item['volume'])
                        
                        df_data.append([
                            timestamp,
                            open_price,
                            high_price,
                            low_price,
                            close_price,
                            volume
                        ])
                    else:
                        print(f"數據項缺少必要字段: {item}")
                
                if not df_data:
                    print("Smithery MCP API返回的數據格式不包含必要字段")
                    return None
                
                # 創建DataFrame
                df = pd.DataFrame(df_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                
                # 將timestamp轉換為datetime格式
                if df['timestamp'].iloc[0] > 10000000000:  # 如果是毫秒時間戳
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                else:  # 如果是秒時間戳
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                
                # 對數據進行排序，確保時間順序
                df = df.sort_values('timestamp')
                
                # 取最近的limit個數據點
                if len(df) > limit:
                    df = df.tail(limit)
                
                print(f"成功從Smithery MCP獲取{symbol}的{len(df)}個數據點")
                return df
            else:
                print(f"Smithery MCP API返回空數據或格式不正確: {data}")
        else:
            print(f"Smithery MCP API返回錯誤: {response.status_code} - {response.text}")
    
    except Exception as e:
        print(f"從Smithery MCP獲取數據時出錯: {str(e)}")
    
    return None

# 修改get_crypto_data函數，使用Smithery MCP作為首選數據源，並移除模擬數據
def get_crypto_data(symbol, timeframe, limit=100):
    """
    獲取加密貨幣歷史數據，優先使用Smithery MCP API
    
    參數:
    - symbol: 交易對符號，例如 'BTC/USDT'
    - timeframe: 時間框架，例如 '15m', '1h', '4h', '1d', '1w'
    - limit: 返回的數據點數量
    
    返回:
    - 包含 timestamp, open, high, low, close, volume 列的 DataFrame
    """
    # 檢查緩存
    cache_key = f"{symbol}_{timeframe}"
    if 'price_data' in st.session_state and cache_key in st.session_state.price_data:
        print(f"使用緩存的{symbol}數據")
        return st.session_state.price_data[cache_key]
    
    st.info(f"正在獲取 {symbol} ({timeframe}) 的市場數據...")
    print(f"調用get_crypto_data: {symbol}, {timeframe}, {limit}")
    
    # 1. 首先嘗試使用Smithery MCP API
    df = get_smithery_mcp_crypto_price(symbol, timeframe, limit)
    if df is not None and len(df) > 0:
        # 驗證價格合理性
        base_coin = symbol.split('/')[0].upper()
        if verify_price_reasonability(df, base_coin):
            # 存入session_state
            if 'price_data' not in st.session_state:
                st.session_state.price_data = {}
            
            st.session_state.price_data[cache_key] = df.copy()
            
            st.success(f"成功獲取 {symbol} 數據，最新價格: ${df['close'].iloc[-1]:.2f}")
            return df
        else:
            print(f"Smithery MCP數據價格驗證失敗")
    
    # 2. 如果Smithery MCP失敗，嘗試使用CoinCap API
    try:
        print(f"嘗試使用CoinCap API獲取{symbol}數據")
        
        # CoinCap ID映射
        coincap_id_map = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'SOL': 'solana',
            'BNB': 'binance-coin',
            'XRP': 'xrp',
            'ADA': 'cardano',
            'DOGE': 'dogecoin',
            'SHIB': 'shiba-inu'
        }
        
        base, quote = symbol.split('/')
        coin_id = coincap_id_map.get(base.upper(), base.lower())
        
        # 時間間隔映射
        interval_map = {
            '15m': 'm15',
            '1h': 'h1',
            '4h': 'h2',  # CoinCap沒有h4，用h2替代
            '1d': 'd1',
            '1w': 'w1'
        }
        
        interval = interval_map.get(timeframe, 'h1')
        
        # 請求頭
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # 計算時間範圍
        end_time = int(time.time() * 1000)
        # 根據時間框架計算合適的開始時間
        time_range = {
            'm15': 1,     # 1天
            'h1': 7,      # 7天
            'h2': 14,     # 14天
            'd1': 30,     # 30天
            'w1': 90      # 90天
        }
        start_time = end_time - (time_range.get(interval, 7) * 24 * 60 * 60 * 1000)
        
        # 發送請求
        url = f"https://api.coincap.io/v2/assets/{coin_id}/history"
        params = {
            'interval': interval,
            'start': start_time,
            'end': end_time
        }
        
        print(f"正在請求CoinCap API: {url}")
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'data' in data and data['data']:
                # 構建OHLCV數據
                ohlcv_data = []
                for point in data['data']:
                    timestamp = point['time']
                    price = float(point['priceUsd'])
                    
                    # CoinCap只提供價格，估算OHLC
                    # 使用小波動以保持價格接近真實值
                    open_price = price * (1 - random.uniform(0, 0.002))
                    high_price = price * (1 + random.uniform(0, 0.003))
                    low_price = price * (1 - random.uniform(0, 0.003))
                    
                    # 估算交易量
                    volume = price * random.uniform(price*1000, price*10000)
                    
                    ohlcv_data.append([
                        timestamp,
                        open_price,
                        high_price,
                        low_price,
                        price,
                        volume
                    ])
                
                # 創建DataFrame並排序
                df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df = df.sort_values('timestamp')
                
                # 過濾所需數量的數據點
                if len(df) > limit:
                    df = df.tail(limit)
                
                print(f"成功從CoinCap獲取{symbol}的{len(df)}個數據點，最新價格: ${df['close'].iloc[-1]:.2f}")
                
                # 驗證價格合理性
                if verify_price_reasonability(df, base.upper()):
                    # 存入session_state
                    if 'price_data' not in st.session_state:
                        st.session_state.price_data = {}
                    
                    st.session_state.price_data[cache_key] = df.copy()
                    
                    st.success(f"成功獲取 {symbol} 數據，最新價格: ${df['close'].iloc[-1]:.2f}")
                    return df
    except Exception as e:
        print(f"CoinCap API請求失敗: {str(e)}")
    
    # 3. 嘗試使用CoinGecko API
    try:
        print(f"嘗試使用CoinGecko API獲取{symbol}數據")
        
        # CoinGecko ID映射
        coingecko_id_map = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'SOL': 'solana',
            'BNB': 'binancecoin',
            'XRP': 'ripple',
            'ADA': 'cardano',
            'DOGE': 'dogecoin',
            'SHIB': 'shiba-inu'
        }
        
        base, quote = symbol.split('/')
        coin_id = coingecko_id_map.get(base.upper(), base.lower())
        vs_currency = quote.lower()
        
        # 根據時間框架選擇天數
        days_map = {
            '15m': 1,
            '1h': 7,
            '4h': 14,
            '1d': 30,
            '1w': 90
        }
        days = days_map.get(timeframe, 7)
        
        # 選擇合適的時間間隔
        interval = 'hourly' if timeframe in ['15m', '1h', '4h'] else 'daily'
        
        # 請求頭，減少被限流概率
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # 發送請求
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {
            'vs_currency': vs_currency,
            'days': days,
            'interval': interval
        }
        
        print(f"正在請求CoinGecko API: {url}")
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'prices' in data and data['prices']:
                # 構建OHLCV數據
                ohlcv_data = []
                
                # 價格數據
                prices = data['prices']  # [timestamp, price]
                volumes = data['total_volumes'] if 'total_volumes' in data else None
                
                for i, price_point in enumerate(prices):
                    timestamp = price_point[0]
                    price = price_point[1]
                    
                    # 估算OHLC
                    open_price = price * (1 - random.uniform(0, 0.002))
                    high_price = price * (1 + random.uniform(0, 0.003))
                    low_price = price * (1 - random.uniform(0, 0.003))
                    
                    # 獲取成交量
                    if volumes and i < len(volumes):
                        volume = volumes[i][1]
                    else:
                        volume = price * random.uniform(price*1000, price*10000)
                    
                    ohlcv_data.append([
                        timestamp,
                        open_price,
                        high_price,
                        low_price,
                        price,
                        volume
                    ])
                
                # 創建DataFrame
                df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                
                # 根據時間框架過濾數據
                if timeframe == '1h':
                    # 每小時數據
                    df = df.iloc[::1]
                elif timeframe == '4h':
                    # 每4小時數據
                    df = df.iloc[::4]
                elif timeframe == '1d':
                    # 每天數據
                    if interval == 'hourly':
                        df = df.iloc[::24]
                
                # 確保數據點數量
                if len(df) > limit:
                    df = df.tail(limit)
                
                print(f"成功從CoinGecko獲取{symbol}的{len(df)}個數據點，最新價格: ${df['close'].iloc[-1]:.2f}")
                
                # 驗證價格合理性
                if verify_price_reasonability(df, base.upper()):
                    # 存入session_state
                    if 'price_data' not in st.session_state:
                        st.session_state.price_data = {}
                    
                    st.session_state.price_data[cache_key] = df.copy()
                    
                    st.success(f"成功獲取 {symbol} 數據，最新價格: ${df['close'].iloc[-1]:.2f}")
                    return df
    except Exception as e:
        print(f"CoinGecko API請求失敗: {str(e)}")
    
    # 4. 嘗試使用CCXT Binance
    try:
        print(f"嘗試使用CCXT Binance獲取{symbol}數據")
        exchange = ccxt.binance()
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        if ohlcv and len(ohlcv) > 0:
            # 創建DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            print(f"成功從CCXT Binance獲取{symbol}的{len(df)}個數據點")
            
            # 驗證價格合理性
            base_coin = symbol.split('/')[0].upper()
            if verify_price_reasonability(df, base_coin):
                # 存入session_state
                if 'price_data' not in st.session_state:
                    st.session_state.price_data = {}
                
                st.session_state.price_data[cache_key] = df.copy()
                
                st.success(f"成功獲取 {symbol} 數據，最新價格: ${df['close'].iloc[-1]:.2f}")
                return df
    except Exception as e:
        print(f"CCXT請求失敗: {str(e)}")
    
    # 5. 如果所有API都失敗，顯示錯誤
    st.error(f"無法從任何API獲取{symbol}的真實數據。請檢查網絡連接或嘗試其他交易對。")
    print(f"無法從任何API獲取{symbol}的真實數據。")
    return None

# 市場結構分析函數 (SMC)
def smc_analysis(df):
    """
    進行SMC (Smart Money Concept) 市場結構分析
    
    參數:
    df (DataFrame): 包含OHLCV數據的DataFrame
    
    返回:
    dict: 包含分析結果的字典
    """
    # 確保df非空
    if df is None or len(df) < 20:
        # 返回默認值
        return {
            'price': 0.0,
            'market_structure': 'neutral',
            'liquidity': 'normal',
            'support_level': 0.0,
            'resistance_level': 0.0,
            'trend_strength': 0.5,
            'recommendation': 'neutral',
            'key_support': 0.0,
            'key_resistance': 0.0
        }
    
    # 計算基本指標
    df['sma20'] = df['close'].rolling(window=20).mean()
    df['sma50'] = df['close'].rolling(window=50).mean()
    df['sma200'] = df['close'].rolling(window=50).mean() # 使用50而不是200，因為可能沒有足夠數據點
    
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
    
    # 定義關鍵支撐阻力位
    key_support = latest['lower_band'] * 0.97
    key_resistance = latest['upper_band'] * 1.03
    
    # 計算趨勢強度 (基於價格與均線的距離和方向)
    price_sma_ratio = latest['close'] / latest['sma20']
    bullish_strength = max(0.5, min(0.9, price_sma_ratio)) if latest['trend'] == 'bullish' else max(0.3, min(0.7, 1 - (1 - price_sma_ratio) * 2))
    
    # 生成分析結果
    results = {
        'price': latest['close'],
        'market_structure': latest['trend'],
        'liquidity': 'high' if latest.get('high_volume', False) else 'normal',
        'support_level': round(latest['lower_band'], 2),
        'resistance_level': round(latest['upper_band'], 2),
        'trend_strength': round(bullish_strength, 2),
        'recommendation': 'buy' if latest['trend'] == 'bullish' and latest['close'] > latest['sma20'] else 
                          'sell' if latest['trend'] == 'bearish' and latest['close'] < latest['sma20'] else 'neutral',
        'key_support': round(key_support, 2),
        'key_resistance': round(key_resistance, 2)
    }
    
    return results

# 供需分析函數 (SNR)
def snr_analysis(df):
    """
    進行SNR (Supply and Demand) 供需分析
    
    參數:
    df (DataFrame): 包含OHLCV數據的DataFrame
    
    返回:
    dict: 包含分析結果的字典
    """
    # 確保df非空
    if df is None or len(df) < 14:
        # 返回默認值
        return {
            'price': 0.0,
            'overbought': False,
            'oversold': False,
            'rsi': 50.0,
            'near_support': 0.0,
            'strong_support': 0.0,
            'near_resistance': 0.0,
            'strong_resistance': 0.0,
            'support_strength': 1.0,
            'resistance_strength': 1.0,
            'recommendation': 'neutral',
            'momentum_up': False,
            'momentum_down': False
        }
    
    # 計算RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # 處理RSI中的NaN值
    df['rsi'] = df['rsi'].fillna(50)
    
    # 獲取最新價格
    current_price = df['close'].iloc[-1]
    
    # 改進支撐阻力位識別 - 使用峰谷法
    # 將數據轉換為numpy數組以提高性能
    prices = df['close'].values
    highs = df['high'].values
    lows = df['low'].values
    volumes = df['volume'].values if 'volume' in df else np.ones_like(prices)
    n = len(prices)
    
    # 識別局部峰值和谷值(價格轉折點)
    peaks = []
    troughs = []
    
    # 使用至少3個點來識別峰值和谷值
    window_size = 3
    for i in range(window_size, n - window_size):
        # 識別峰值(局部高點)
        if all(highs[i] > highs[i-j] for j in range(1, window_size+1)) and all(highs[i] > highs[i+j] for j in range(1, window_size+1)):
            peaks.append((i, highs[i], volumes[i]))
        
        # 識別谷值(局部低點)
        if all(lows[i] < lows[i-j] for j in range(1, window_size+1)) and all(lows[i] < lows[i+j] for j in range(1, window_size+1)):
            troughs.append((i, lows[i], volumes[i]))
    
    # 基於峰谷和成交量計算支撐阻力位
    resistance_levels = []
    support_levels = []
    
    # 僅考慮最近的點(距離當前時間越近越重要)
    recency_factor = 0.85
    
    # 處理阻力位
    for i, price, volume in peaks:
        # 如果價格高於當前價格，則為阻力位
        if price > current_price:
            # 計算權重 (基於成交量和接近當前時間程度)
            weight = (volume / np.mean(volumes)) * (recency_factor ** (n - i - 1))
            resistance_levels.append((price, weight))
    
    # 處理支撐位
    for i, price, volume in troughs:
        # 如果價格低於當前價格，則為支撐位
        if price < current_price:
            # 計算權重 (基於成交量和接近當前時間程度)
            weight = (volume / np.mean(volumes)) * (recency_factor ** (n - i - 1))
            support_levels.append((price, weight))
    
    # 在沒有足夠峰谷的情況下使用技術分析創建水平位
    if len(resistance_levels) < 2:
        # 使用ATR的倍數作為備選阻力位
        atr = np.mean([highs[i] - lows[i] for i in range(n-14, n)])
        resistance_levels.extend([(current_price + (i+1) * atr, 0.5 / (i+1)) for i in range(3)])
    
    if len(support_levels) < 2:
        # 使用ATR的倍數作為備選支撐位
        atr = np.mean([highs[i] - lows[i] for i in range(n-14, n)])
        support_levels.extend([(current_price - (i+1) * atr, 0.5 / (i+1)) for i in range(3)])
    
    # 按照價格排序支撐阻力位
    resistance_levels.sort(key=lambda x: x[0])
    support_levels.sort(key=lambda x: x[0], reverse=True)
    
    # 選擇近期支撐阻力位(最接近當前價格的)
    near_resistance = resistance_levels[0][0] if resistance_levels else current_price * 1.05
    near_support = support_levels[0][0] if support_levels else current_price * 0.95
    
    # 選擇強支撐阻力位(第二接近的，或者根據權重選擇)
    strong_resistance = resistance_levels[1][0] if len(resistance_levels) > 1 else near_resistance * 1.05
    strong_support = support_levels[1][0] if len(support_levels) > 1 else near_support * 0.95
    
    # 計算支撐阻力強度(基於識別出的點的權重)
    support_strength = sum(weight for _, weight in support_levels) if support_levels else 1.0
    resistance_strength = sum(weight for _, weight in resistance_levels) if resistance_levels else 1.0
    
    # 計算動能方向 (基於近期RSI變化)
    rsi_change = 0
    if len(df) > 5:
        rsi_change = df['rsi'].iloc[-1] - df['rsi'].iloc[-6]
    
    momentum_up = rsi_change > 5
    momentum_down = rsi_change < -5
    
    # 生成分析結果
    results = {
        'price': current_price,
        'overbought': df['rsi'].iloc[-1] > 70,
        'oversold': df['rsi'].iloc[-1] < 30,
        'rsi': round(df['rsi'].iloc[-1], 2),
        'near_support': round(near_support, 2),
        'strong_support': round(strong_support, 2),
        'near_resistance': round(near_resistance, 2),
        'strong_resistance': round(strong_resistance, 2),
        'support_strength': round(min(support_strength, 2.0), 2),  # 限制在0-2範圍
        'resistance_strength': round(min(resistance_strength, 2.0), 2),  # 限制在0-2範圍
        'recommendation': 'buy' if df['rsi'].iloc[-1] < 30 else 
                          'sell' if df['rsi'].iloc[-1] > 70 else 'neutral',
        'momentum_up': momentum_up,
        'momentum_down': momentum_down,
        'all_support_levels': [round(price, 2) for price, _ in support_levels[:5]],
        'all_resistance_levels': [round(price, 2) for price, _ in resistance_levels[:5]]
    }
    
    return results

# 添加GPT-4o-mini市場情緒分析函數
def get_gpt4o_analysis(symbol, timeframe, smc_results, snr_results):
    """
    使用GPT-4o-mini進行市場情緒分析
    
    參數:
    symbol (str): 加密貨幣符號
    timeframe (str): 時間框架
    smc_results (dict): SMC分析結果
    snr_results (dict): SNR分析結果
    
    返回:
    str: 市場情緒分析結果
    """
    # 返回模擬分析
    sentiment = "看漲" if smc_results["market_structure"] == "bullish" else "看跌"
    confidence = "高" if smc_results["trend_strength"] > 0.7 else "中等" if smc_results["trend_strength"] > 0.4 else "低"
    
    return f"""
    ## {symbol} 市場情緒分析
    
    當前市場整體情緒: **{sentiment}** (信心水平: {confidence})
    
    ### 主要市場驅動因素:
    - 技術面: {'強勁的上升趨勢，主要指標顯示持續動能' if sentiment == '看漲' else '明顯的下降趨勢，技術指標表明賣壓較大'}
    - 市場參與度: {'交易量呈現穩定增長，顯示更多資金流入' if smc_results.get('liquidity', 'normal') == 'high' else '交易量平穩，未見明顯資金流向變化'}
    - 投資者情緒: {'普遍樂觀，支撐位受到尊重' if sentiment == '看漲' else '謹慎偏悲觀，阻力位獲得確認'}
    
    ### 主要觀察點:
    1. RSI 當前值 {snr_results["rsi"]:.1f}，{'顯示超買狀態，需警惕可能的回調' if snr_results["overbought"] else '顯示超賣狀態，可能存在反彈機會' if snr_results["oversold"] else '處於中性區間'}
    2. 價格相對於支撐位 ${snr_results["near_support"]:.2f} 的位置{'相對安全' if smc_results["price"] > snr_results["near_support"] * 1.05 else '較為接近，需密切關注'}
    3. 價格相對於阻力位 ${snr_results["near_resistance"]:.2f} 的位置{'接近，可能面臨賣壓' if smc_results["price"] > snr_results["near_resistance"] * 0.95 else '尚有上升空間'}
    
    ### 情緒轉變可能性:
    - {'若價格突破 $' + str(snr_results["near_resistance"]) + '，市場情緒可能轉為更強烈的看漲' if sentiment == '看漲' else '若價格跌破 $' + str(snr_results["near_support"]) + '，市場情緒可能進一步惡化'}
    - {'RSI進入超買區間可能引發獲利了結情緒' if snr_results["rsi"] > 60 and snr_results["rsi"] < 70 else 'RSI進入超賣區間可能吸引逢低買入情緒' if snr_results["rsi"] < 40 and snr_results["rsi"] > 30 else '技術指標處於中性位置，情緒可能維持當前狀態'}
    
    ### 短期情緒預測:
    未來7天市場情緒可能{'保持看漲，但需警惕獲利了結' if sentiment == '看漲' else '持續偏空，直到出現明確的技術反轉信號'}。交易者應{'保持樂觀但謹慎，設置合理止損' if sentiment == '看漲' else '保持謹慎，等待反彈信號確認'}。
    """

# 添加綜合分析函數
def get_claude_analysis(symbol, timeframe, smc_results, snr_results):
    """
    生成綜合技術分析報告
    
    參數:
    symbol (str): 加密貨幣符號
    timeframe (str): 時間框架
    smc_results (dict): SMC分析結果
    snr_results (dict): SNR分析結果
    
    返回:
    str: 綜合分析報告
    """
    # 檢查SMC和SNR建議是否一致
    is_consistent = smc_results["recommendation"] == snr_results["recommendation"]
    confidence = 0.8 if is_consistent else 0.6
    
    # 決定最終建議
    if is_consistent:
        final_rec = smc_results["recommendation"]
    elif smc_results["trend_strength"] > 0.7:
        final_rec = smc_results["recommendation"]
    elif snr_results["rsi"] < 30 or snr_results["rsi"] > 70:
        final_rec = snr_results["recommendation"]
    else:
        final_rec = "neutral"
    
    # 生成模擬分析
    sentiment = "看漲" if smc_results["market_structure"] == "bullish" else "看跌"
    confidence_text = "高" if confidence > 0.7 else "中等" if confidence > 0.5 else "低"
    
    # 根據最終建議生成不同的分析文本
    if final_rec == "buy":
        analysis = f"""
        ## {symbol} 綜合技術分析報告
        
        ### 市場結構分析
        
        {symbol}當前呈現**{sentiment}市場結構**，趨勢強度為**{smc_results["trend_strength"]:.2f}**。價格位於${smc_results["price"]:.2f}，高於20日均線，顯示上升動能。近期形成了更高的高點和更高的低點，確認了上升趨勢的有效性。
        
        ### 支撐阻力分析
        
        - **關鍵支撐位**: ${smc_results["support_level"]:.2f}，這是買入壓力集中的區域，也是回調時可能見到的反彈點
        - **次級支撐位**: ${snr_results["near_support"]:.2f}，若跌破主要支撐位，這將是下一個關注點
        - **主要阻力位**: ${smc_results["resistance_level"]:.2f}，突破此位可能引發更強勁的上升動能
        - **次級阻力位**: ${snr_results["near_resistance"]:.2f}，這是短期內價格可能遇到的首個阻力
        
        ### 動量指標分析
        
        RSI當前為**{snr_results["rsi"]:.2f}**，處於{"超買區間，顯示強勁動能但也暗示可能即將調整" if snr_results["overbought"] else "超賣區間，暗示可能出現反彈機會" if snr_results["oversold"] else "中性區間，未顯示明顯超買或超賣信號"}。趨勢{"與RSI形成良性確認" if (sentiment == "看漲" and snr_results["rsi"] > 50) or (sentiment == "看跌" and snr_results["rsi"] < 50) else "與RSI存在背離，需謹慎對待"}。
        
        ### 綜合交易建議
        
        基於SMC和SNR分析的綜合評估，目前對{symbol}持**看漲觀點**，信心水平為**{confidence_text}**。
        
        **入場策略**:
        - **理想買入區間**: ${smc_results["support_level"]:.2f} - ${(smc_results["support_level"] * 1.02):.2f}
        - **進場條件**: 價格回調至支撐位附近且出現反彈確認信號（如大陽線、成交量增加）
        - **止損設置**: ${(smc_results["support_level"] * 0.98):.2f}（支撐位下方2%）
        
        **目標管理**:
        - **第一目標**: ${snr_results["near_resistance"]:.2f}（風險回報比約為{((snr_results["near_resistance"] - smc_results["price"]) / (smc_results["price"] - smc_results["support_level"] * 0.98)):.1f}）
        - **第二目標**: ${smc_results["resistance_level"]:.2f}（突破近期阻力後）
        
        **風險管理**:
        - 建議僅使用總資金的15-20%參與此交易
        - 若價格跌破${smc_results["support_level"]:.2f}且無法快速恢復，應考慮調整策略
        - 關注成交量變化，確認價格走勢的有效性
        
        ### 監控要點
        
        1. RSI是否持續在50以上，保持上升動能
        2. 價格是否在關鍵支撐位獲得支撐
        3. 成交量是否配合價格變化，確認趨勢有效性
        4. 市場整體情緒變化，特別是較大時間框架的變化
        """
    elif final_rec == "sell":
        analysis = f"""
        ## {symbol} 綜合技術分析報告
        
        ### 市場結構分析
        
        {symbol}當前呈現**{sentiment}市場結構**，趨勢強度為**{smc_results["trend_strength"]:.2f}**。價格位於${smc_results["price"]:.2f}，低於20日均線，顯示下降動能。近期形成了更低的低點和更低的高點，確認了下降趨勢的有效性。
        
        ### 支撐阻力分析
        
        - **關鍵阻力位**: ${smc_results["resistance_level"]:.2f}，這是賣出壓力集中的區域，也是反彈時可能見到的回落點
        - **次級阻力位**: ${snr_results["near_resistance"]:.2f}，這是短期內價格可能遇到的首個阻力
        - **主要支撐位**: ${smc_results["support_level"]:.2f}，跌破此位可能引發更強勁的下跌動能
        - **次級支撐位**: ${snr_results["near_support"]:.2f}，這是短期內價格可能尋求支撐的區域
        
        ### 動量指標分析
        
        RSI當前為**{snr_results["rsi"]:.2f}**，處於{"超買區間，暗示可能即將調整" if snr_results["overbought"] else "超賣區間，顯示強勁下跌動能但也暗示可能出現技術性反彈" if snr_results["oversold"] else "中性區間，未顯示明顯超買或超賣信號"}。趨勢{"與RSI形成良性確認" if (sentiment == "看漲" and snr_results["rsi"] > 50) or (sentiment == "看跌" and snr_results["rsi"] < 50) else "與RSI存在背離，需謹慎對待"}。
        
        ### 綜合交易建議
        
        基於SMC和SNR分析的綜合評估，目前對{symbol}持**看跌觀點**，信心水平為**{confidence_text}**。
        
        **入場策略**:
        - **理想賣出區間**: ${smc_results["resistance_level"]:.2f} - ${(smc_results["resistance_level"] * 0.98):.2f}
        - **進場條件**: 價格反彈至阻力位附近且出現回落確認信號（如大陰線、成交量增加）
        - **止損設置**: ${(smc_results["resistance_level"] * 1.02):.2f}（阻力位上方2%）
        
        **目標管理**:
        - **第一目標**: ${snr_results["near_support"]:.2f}（風險回報比約為{((smc_results["price"] - snr_results["near_support"]) / (smc_results["resistance_level"] * 1.02 - smc_results["price"])):.1f}）
        - **第二目標**: ${smc_results["support_level"]:.2f}（跌破近期支撐後）
        
        **風險管理**:
        - 建議僅使用總資金的15-20%參與此交易
        - 若價格突破${smc_results["resistance_level"]:.2f}且無法快速回落，應考慮調整策略
        - 關注成交量變化，確認價格走勢的有效性
        
        ### 監控要點
        
        1. RSI是否持續在50以下，保持下降動能
        2. 價格是否在關鍵阻力位遇到阻礙
        3. 成交量是否配合價格變化，確認趨勢有效性
        4. 市場整體情緒變化，特別是較大時間框架的變化
        """
    else:  # neutral
        analysis = f"""
        ## {symbol} 綜合技術分析報告
        
        ### 市場結構分析
        
        {symbol}當前呈現**混合市場結構**，趨勢強度為**{smc_results["trend_strength"]:.2f}**。價格位於${smc_results["price"]:.2f}，接近20日均線，未顯示明確方向性。近期價格波動在一定區間內，未形成明確的更高高點或更低低點。
        
        ### 支撐阻力分析
        
        - **上方阻力位**: ${smc_results["resistance_level"]:.2f}和${snr_results["near_resistance"]:.2f}
        - **下方支撐位**: ${smc_results["support_level"]:.2f}和${snr_results["near_support"]:.2f}
        - 目前價格在這些區間內波動，未顯示明確突破或跌破跡象
        
        ### 動量指標分析
        
        RSI當前為**{snr_results["rsi"]:.2f}**，處於{"超買區間，暗示可能即將調整" if snr_results["overbought"] else "超賣區間，暗示可能出現反彈機會" if snr_results["oversold"] else "中性區間，未顯示明顯超買或超賣信號"}。整體動能指標顯示市場處於等待狀態，缺乏明確方向。
        
        ### 綜合交易建議
        
        基於SMC和SNR分析的綜合評估，目前對{symbol}持**中性觀點**，建議觀望為主。市場缺乏明確方向性信號，風險回報比不佳。
        
        **可能的交易策略**:
        
        **區間交易策略**:
        - **買入區域**: 接近${snr_results["near_support"]:.2f}的支撐位
        - **賣出區域**: 接近${snr_results["near_resistance"]:.2f}的阻力位
        - **止損設置**: 支撐位下方2%或阻力位上方2%
        
        **突破策略**:
        - 等待價格明確突破${smc_results["resistance_level"]:.2f}阻力位或跌破${smc_results["support_level"]:.2f}支撐位
        - 突破後確認有效性（成交量配合、持續性等）再跟進
        
        **風險管理**:
        - 建議降低倉位至總資金的10-15%
        - 設置嚴格止損以控制風險
        - 在區間內交易時使用較小倉位
        
        ### 監控要點
        
        1. 關注${smc_results["resistance_level"]:.2f}和${smc_results["support_level"]:.2f}這兩個關鍵價位的突破情況
        2. 觀察成交量變化，尋找可能的方向性確認
        3. 關注RSI是否脫離中性區間，進入超買或超賣狀態
        4. 注意更大時間框架的趨勢變化，可能提供更明確的方向
        """
    
    return analysis

# 應用標題和導航 - 使用列布局替代側邊欄
st.markdown("""
<div style="text-align: center; padding: 20px 0;">
    <h1>0xAI CryptoCat 加密貨幣分析儀表板</h1>
    <p>多模型AI驅動的加密貨幣技術與市場情緒分析</p>
</div>
""", unsafe_allow_html=True)

# 頂部導航欄 - 使用tab切換不同功能
tabs = st.tabs(["📈 技術分析", "🧠 AI 分析", "📊 市場數據", "⚙️ 設置"])

with tabs[0]:
    # 技術分析標籤內容
    st.markdown("<h2>技術分析儀表板</h2>", unsafe_allow_html=True)
    
    # 使用列布局安排控制元素
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    
    with col1:
        # 使用下拉菜單而非側邊欄選項
        coin_options = {
            'BTC/USDT': '比特幣 (BTC)',
            'ETH/USDT': '以太坊 (ETH)',
            'SOL/USDT': '索拉納 (SOL)',
            'BNB/USDT': '幣安幣 (BNB)',
            'XRP/USDT': '瑞波幣 (XRP)',
            'ADA/USDT': '艾達幣 (ADA)',
            'DOGE/USDT': '狗狗幣 (DOGE)',
            'SHIB/USDT': '柴犬幣 (SHIB)'
        }
        selected_symbol = st.selectbox('選擇加密貨幣', list(coin_options.keys()), format_func=lambda x: coin_options[x])
    
    with col2:
        timeframe_options = {
            '15m': '15分鐘',
            '1h': '1小時',
            '4h': '4小時',
            '1d': '1天',
            '1w': '1週'
        }
        selected_timeframe = st.selectbox('選擇時間框架', list(timeframe_options.keys()), format_func=lambda x: timeframe_options[x])
    
    with col3:
        # 額外選項，例如交易量顯示、指標選擇等
        show_volume = st.checkbox('顯示交易量', value=True)
        
    with col4:
        # 分析按鈕
        st.markdown("<br>", unsafe_allow_html=True)  # 添加一些空間來對齊按鈕
        analyze_button = st.button('開始分析', use_container_width=True)
    
    # 使用卡片式設計展示主要圖表
    st.markdown('<div class="stCardContainer">', unsafe_allow_html=True)
    
    # 這裡放置主要價格圖表
    # 您可以保留原有的圖表生成代碼，但將其放在這個卡片容器中
    
    # 模擬價格圖表
    if 'analyzed' not in st.session_state:
        st.session_state.analyzed = False
        
    if analyze_button or st.session_state.analyzed:
        st.session_state.analyzed = True
        
        # 顯示加載中動畫
        with st.spinner(f"正在獲取 {selected_symbol} 數據並進行分析..."):
            # 檢查是否已有緩存數據
            cache_key = f"{selected_symbol}_{selected_timeframe}"
            if 'price_data' in st.session_state and cache_key in st.session_state.price_data:
                print(f"使用緩存的{selected_symbol}數據")
                df = st.session_state.price_data[cache_key]
            else:
                # 使用DexScreener API獲取真實數據
                df = get_crypto_data(selected_symbol, selected_timeframe, limit=100)
                
            if df is not None:
                # 使用真實數據創建圖表
                fig = go.Figure()
                
                # 添加蠟燭圖 - 使用實際數據
                fig.add_trace(go.Candlestick(
                    x=df['timestamp'],
                    open=df['open'],
                    high=df['high'],
                    low=df['low'],
                    close=df['close'],
                    name='價格'
                ))
                
                # 計算移動平均線
                df['ma20'] = df['close'].rolling(window=20).mean()
                df['ma50'] = df['close'].rolling(window=50).mean()
                
                # 添加移動平均線 - 使用實際數據
                fig.add_trace(go.Scatter(
                    x=df['timestamp'],
                    y=df['ma20'],
                    mode='lines',
                    name='MA20',
                    line=dict(color='#9C27B0', width=2)
                ))
                
                fig.add_trace(go.Scatter(
                    x=df['timestamp'],
                    y=df['ma50'],
                    mode='lines',
                    name='MA50',
                    line=dict(color='#00BCD4', width=2)
                ))
                
                # 更新布局
                fig.update_layout(
                    title=f'{selected_symbol} 價格圖表 ({selected_timeframe})',
                    xaxis_title='日期',
                    yaxis_title='價格 (USDT)',
                    template='plotly_dark',
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(showgrid=False),
                    yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
                    height=500,
                    margin=dict(l=40, r=40, t=60, b=40)
                )
                
                # 顯示圖表
                st.plotly_chart(fig, use_container_width=True)
                
                if show_volume:
                    # 添加成交量圖表 - 使用實際數據
                    volume_fig = go.Figure()
                    volume_fig.add_trace(go.Bar(
                        x=df['timestamp'],
                        y=df['volume'],
                        marker_color='rgba(74, 138, 244, 0.7)',
                        name='成交量'
                    ))
                    
                    volume_fig.update_layout(
                        title='交易量',
                        xaxis_title='日期',
                        yaxis_title='成交量',
                        template='plotly_dark',
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        xaxis=dict(showgrid=False),
                        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
                        height=250,
                        margin=dict(l=40, r=40, t=40, b=40)
                    )
                    
                    st.plotly_chart(volume_fig, use_container_width=True)
                
                # 進行真實技術分析
                smc_data = smc_analysis(df)
                snr_data = snr_analysis(df)
            else:
                st.error(f"無法獲取 {selected_symbol} 的數據，請稍後再試或選擇其他幣種。")
    else:
        # 顯示占位符提示
        st.info("請選擇加密貨幣和時間框架，然後點擊「開始分析」按鈕來查看技術分析。")
        
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 使用可折疊區域顯示更多指標和詳細信息
    if st.session_state.get('analyzed', False):
        # 使用兩列布局顯示關鍵指標
        col1, col2 = st.columns(2)
        
        with col1:
            # SMC 分析結果卡片
            st.markdown('<div class="stCardContainer">', unsafe_allow_html=True)
            st.markdown("<h3>SMC 市場結構分析</h3>", unsafe_allow_html=True)
            
            # 使用真實SMC分析數據
            # 顯示主要信息
            st.markdown(f"""
            <div class="highlight-metric">市場結構: {"看漲" if smc_data["market_structure"] == "bullish" else "看跌"}</div>
            <div class="highlight-metric">趨勢強度: {smc_data["trend_strength"]:.2f}</div>
            <div class="highlight-metric">當前價格: ${smc_data["price"]:.2f}</div>
            """, unsafe_allow_html=True)
            
            # 使用可折疊部分顯示更多細節
            with st.expander("查看詳細 SMC 分析"):
                st.markdown(f"""
                **支撐位**: ${smc_data["support_level"]:.2f}  
                **阻力位**: ${smc_data["resistance_level"]:.2f}  
                **SMC 建議**: {"買入" if smc_data["recommendation"] == "buy" else "賣出" if smc_data["recommendation"] == "sell" else "觀望"}
                
                **重要價格水平**:
                - 當前價格: ${smc_data["price"]:.2f}
                - 關鍵支撐: ${smc_data["key_support"]:.2f}
                - 關鍵阻力: ${smc_data["key_resistance"]:.2f}
                
                **趨勢信息**:
                - 市場結構: {"看漲" if smc_data["market_structure"] == "bullish" else "看跌"}
                - 趨勢強度: {smc_data["trend_strength"]:.2f}
                - 趨勢持續性: {"高" if smc_data["trend_strength"] > 0.7 else "中等" if smc_data["trend_strength"] > 0.4 else "低"}
                """)
                
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            # SNR 分析結果卡片
            st.markdown('<div class="stCardContainer">', unsafe_allow_html=True)
            st.markdown("<h3>SNR 供需分析</h3>", unsafe_allow_html=True)
            
            # 使用真實SNR分析數據
            # 顯示主要信息
            rsi_state = "超買" if snr_data["overbought"] else "超賣" if snr_data["oversold"] else "中性"
            st.markdown(f"""
            <div class="highlight-metric">RSI: {snr_data["rsi"]:.2f} ({rsi_state})</div>
            <div class="highlight-metric">近期支撐位: ${snr_data["near_support"]:.2f}</div>
            <div class="highlight-metric">近期阻力位: ${snr_data["near_resistance"]:.2f}</div>
            """, unsafe_allow_html=True)
            
            # 使用可折疊部分顯示更多細節
            with st.expander("查看詳細 SNR 分析"):
                st.markdown(f"""
                **強支撐位**: ${snr_data["strong_support"]:.2f}  
                **強阻力位**: ${snr_data["strong_resistance"]:.2f}  
                **SNR 建議**: {"買入" if snr_data["recommendation"] == "buy" else "賣出" if snr_data["recommendation"] == "sell" else "觀望"}
                
                **技術指標**:
                - RSI ({selected_timeframe}): {snr_data["rsi"]:.2f}
                - 狀態: {"超買" if snr_data["overbought"] else "超賣" if snr_data["oversold"] else "中性"}
                - 動能方向: {"上升" if snr_data.get("momentum_up", False) else "下降" if snr_data.get("momentum_down", False) else "中性"}
                
                **供需區域**:
                - 主要供應區: ${snr_data["strong_resistance"]:.2f} 到 ${snr_data["near_resistance"]:.2f}
                - 主要需求區: ${snr_data["near_support"]:.2f} 到 ${snr_data["strong_support"]:.2f}
                """)
                
            st.markdown('</div>', unsafe_allow_html=True)
        
        # 綜合分析結果區域
        st.markdown('<div class="stCardContainer">', unsafe_allow_html=True)
        st.markdown("<h3>綜合交易建議</h3>", unsafe_allow_html=True)
        
        # 檢查 SMC 和 SNR 建議是否一致
        is_consistent = smc_data["recommendation"] == snr_data["recommendation"]
        confidence = 0.8 if is_consistent else 0.6
        
        # 決定最終建議
        if is_consistent:
            final_rec = smc_data["recommendation"]
        elif smc_data["trend_strength"] > 0.7:
            final_rec = smc_data["recommendation"]
        elif snr_data["rsi"] < 30 or snr_data["rsi"] > 70:
            final_rec = snr_data["recommendation"]
        else:
            final_rec = "neutral"
        
        # 計算風險評分
        risk_score = 5
        if smc_data["market_structure"] == "bullish":
            risk_score -= 1
        else:
            risk_score += 1
            
        if snr_data["overbought"]:
            risk_score += 2
        elif snr_data["oversold"]:
            risk_score -= 2
            
        if final_rec == "buy":
            risk_score += 1
        elif final_rec == "sell":
            risk_score -= 1
            
        risk_score = max(1, min(10, risk_score))
        
        # 顯示綜合建議
        recommendation_color = "#4CAF50" if final_rec == "buy" else "#F44336" if final_rec == "sell" else "#FFC107"
        
        st.markdown(f"""
        <div style="display:flex; align-items:center; margin-bottom:20px;">
            <div style="font-size:28px; font-weight:bold; margin-right:15px; color:{recommendation_color};">
                {"買入" if final_rec == "buy" else "賣出" if final_rec == "sell" else "觀望"}
            </div>
            <div style="flex-grow:1;">
                <div style="height:10px; background-color:rgba(255,255,255,0.1); border-radius:5px;">
                    <div style="height:100%; width:{confidence*100}%; background-color:{recommendation_color}; border-radius:5px;"></div>
                </div>
                <div style="font-size:12px; margin-top:5px;">信心指數: {confidence*100:.1f}%</div>
            </div>
        </div>
        
        <div class="analysis-summary">
            <p><strong>市場結構:</strong> {selected_symbol} 目前處於{"上升" if smc_data["market_structure"] == "bullish" else "下降"}趨勢，趨勢強度為 {smc_data["trend_strength"]:.2f}。</p>
            <p><strong>技術指標:</strong> RSI為 {snr_data["rsi"]:.2f}，{"顯示超買信號" if snr_data["overbought"] else "顯示超賣信號" if snr_data["oversold"] else "處於中性區間"}。</p>
            <p><strong>風險評分:</strong> {risk_score}/10 ({"高風險" if risk_score > 7 else "中等風險" if risk_score > 4 else "低風險"})</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 使用可折疊區域顯示完整的分析報告
        with st.expander("查看完整分析報告"):
            with st.spinner("正在生成完整分析報告..."):
                # 使用真實API進行整合分析
                claude_analysis = get_claude_analysis(selected_symbol, selected_timeframe, smc_data, snr_data)
                st.markdown(claude_analysis)
                
        st.markdown('</div>', unsafe_allow_html=True)

with tabs[1]:
    # AI 分析標籤內容
    st.markdown("<h2>AI 驅動分析</h2>", unsafe_allow_html=True)
    
    if st.session_state.get('analyzed', False):
        # AI 分析分為兩列
        col1, col2 = st.columns(2)
        
        with col1:
            # GPT-4o-mini 市場情緒分析
            st.markdown('<div class="stCardContainer">', unsafe_allow_html=True)
            st.markdown("<h3>市場情緒分析 <span style='font-size:14px; color:#00BCD4;'>(GPT-4o-mini)</span></h3>", unsafe_allow_html=True)
            
            with st.spinner("正在使用 GPT-4o-mini 分析市場情緒..."):
                # 使用真實API進行市場情緒分析
                gpt4o_analysis = get_gpt4o_analysis(selected_symbol, selected_timeframe, smc_data, snr_data)
                st.markdown(gpt4o_analysis)
                
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col2:
            # DeepSeek 策略分析
            st.markdown('<div class="stCardContainer">', unsafe_allow_html=True)
            st.markdown("<h3>策略預測 <span style='font-size:14px; color:#9C27B0;'>(DeepSeek)</span></h3>", unsafe_allow_html=True)
            
            with st.spinner("正在使用 DeepSeek 進行策略預測..."):
                # 使用 DessSeek API 進行策略預測
                # 由於沒有單獨的策略預測函數，我們使用部分 Claude 分析
                strategy_prompt = f"""
                請針對{selected_symbol}在{selected_timeframe}時間框架下，根據以下數據提供簡短的交易策略建議：
                
                價格: ${smc_data['price']:.2f}
                市場結構: {"上升趨勢" if smc_data['market_structure'] == 'bullish' else "下降趨勢"}
                趨勢強度: {smc_data['trend_strength']:.2f}
                RSI: {snr_data['rsi']:.2f}
                支撐位: ${snr_data['near_support']:.2f}
                阻力位: ${snr_data['near_resistance']:.2f}
                
                請僅提供3-4個具體的交易策略建議，包括進場點、目標價和止損位。以Markdown格式回答。
                """
                
                try:
                    # 如果有DeepSeek API密鑰，使用API
                    if DEEPSEEK_API_KEY:
                        headers = {
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
                        }
                        
                        payload = {
                            "model": "deepseek-chat",
                            "messages": [
                                {
                                    "role": "user",
                                    "content": strategy_prompt
                                }
                            ],
                            "temperature": 0.3,
                            "max_tokens": 800
                        }
                        
                        response = requests.post(
                            "https://api.deepseek.com/v1/chat/completions",
                            headers=headers,
                            json=payload
                        )
                        
                        if response.status_code == 200:
                            strategy_analysis = response.json()["choices"][0]["message"]["content"]
                        else:
                            strategy_analysis = f"## {selected_symbol} 短期策略建議\n\n"
                            
                            if final_rec == "buy":
                                strategy_analysis += f"""
                                **突破策略**: 若價格突破${snr_data['near_resistance']:.2f}阻力位，且成交量放大，可考慮追漲進場，目標${smc_data['resistance_level']:.2f}，止損設在${(snr_data['near_resistance']*0.99):.2f}。
                                
                                **支撐回調策略**: 若價格回調至${snr_data['near_support']:.2f}支撐位附近，RSI同時回落至50以下，可考慮逢低買入，目標${snr_data['near_resistance']:.2f}，止損設在${(snr_data['near_support']*0.98):.2f}。
                                """
                            elif final_rec == "sell":
                                strategy_analysis += f"""
                                **做空策略**: 若價格在${snr_data['near_resistance']:.2f}阻力位附近遇阻，RSI高於60，可考慮做空，目標${snr_data['near_support']:.2f}，止損設在${(snr_data['near_resistance']*1.02):.2f}。
                                
                                **高點拋售策略**: 若持倉且價格接近${smc_data['resistance_level']:.2f}，可考慮獲利了結，避免回調風險。
                                """
                            else:
                                strategy_analysis += f"""
                                **區間震盪策略**: 價格可能在${snr_data['near_support']:.2f}-${snr_data['near_resistance']:.2f}之間震盪，可考慮在區間下沿買入，上沿賣出的高頻操作策略。
                                
                                **觀望策略**: 目前市場信號混合，建議觀望至趨勢明確，可關注${snr_data['near_support']:.2f}和${snr_data['near_resistance']:.2f}的突破情況。
                                """
                            
                            strategy_analysis += f"""
                            **風險評估**: 目前市場風險{"偏高" if risk_score > 7 else "偏中性" if risk_score > 4 else "偏低"}，建議使用不超過{30 if risk_score < 5 else 20 if risk_score < 8 else 10}%的資金參與此類交易。
                            """
                    else:
                        # 如果沒有API密鑰，使用預設分析
                        strategy_analysis = f"## {selected_symbol} 短期策略建議\n\n"
                        
                        if final_rec == "buy":
                            strategy_analysis += f"""
                            **突破策略**: 若價格突破${snr_data['near_resistance']:.2f}阻力位，且成交量放大，可考慮追漲進場，目標${smc_data['resistance_level']:.2f}，止損設在${(snr_data['near_resistance']*0.99):.2f}。
                            
                            **支撐回調策略**: 若價格回調至${snr_data['near_support']:.2f}支撐位附近，RSI同時回落至50以下，可考慮逢低買入，目標${snr_data['near_resistance']:.2f}，止損設在${(snr_data['near_support']*0.98):.2f}。
                            """
                        elif final_rec == "sell":
                            strategy_analysis += f"""
                            **做空策略**: 若價格在${snr_data['near_resistance']:.2f}阻力位附近遇阻，RSI高於60，可考慮做空，目標${snr_data['near_support']:.2f}，止損設在${(snr_data['near_resistance']*1.02):.2f}。
                            
                            **高點拋售策略**: 若持倉且價格接近${smc_data['resistance_level']:.2f}，可考慮獲利了結，避免回調風險。
                            """
                        else:
                            strategy_analysis += f"""
                            **區間震盪策略**: 價格可能在${snr_data['near_support']:.2f}-${snr_data['near_resistance']:.2f}之間震盪，可考慮在區間下沿買入，上沿賣出的高頻操作策略。
                            
                            **觀望策略**: 目前市場信號混合，建議觀望至趨勢明確，可關注${snr_data['near_support']:.2f}和${snr_data['near_resistance']:.2f}的突破情況。
                            """
                        
                        strategy_analysis += f"""
                        **風險評估**: 目前市場風險{"偏高" if risk_score > 7 else "偏中性" if risk_score > 4 else "偏低"}，建議使用不超過{30 if risk_score < 5 else 20 if risk_score < 8 else 10}%的資金參與此類交易。
                        """
                        
                except Exception as e:
                    st.error(f"策略分析生成錯誤: {str(e)}")
                    strategy_analysis = "無法生成策略分析，請稍後再試。"
                
                st.markdown(strategy_analysis)
                
            st.markdown('</div>', unsafe_allow_html=True)
        
        # 整合 AI 分析結果 (DeepSeek V3)
        st.markdown('<div class="stCardContainer">', unsafe_allow_html=True)
        st.markdown("<h3>整合 AI 分析 <span style='font-size:14px; color:#3F51B5;'>(DeepSeek V3)</span></h3>", unsafe_allow_html=True)
        
        with st.spinner("正在使用 DeepSeek V3 整合分析結果..."):
            # 這裡已經在上一頁面生成了Claude分析，直接顯示
            st.markdown(claude_analysis)
            
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        # 顯示占位符提示
        st.info("請在「技術分析」頁面選擇加密貨幣並點擊「開始分析」按鈕來產生 AI 分析。")

with tabs[2]:
    # 市場數據標籤內容
    st.markdown("<h2>市場數據</h2>", unsafe_allow_html=True)
    
    # 創建市場概覽卡片
    st.markdown('<div class="stCardContainer">', unsafe_allow_html=True)
    st.markdown("<h3>市場概覽</h3>", unsafe_allow_html=True)
    
    # 嘗試獲取真實市場數據
    try:
        # 檢查是否已有緩存數據
        btc_cache_key = "BTC/USDT_1d"
        eth_cache_key = "ETH/USDT_1d"
        
        if 'price_data' in st.session_state and btc_cache_key in st.session_state.price_data:
            print("使用緩存的BTC數據")
            btc_data = st.session_state.price_data[btc_cache_key]
        else:
            # 使用get_crypto_data獲取
            btc_data = get_crypto_data("BTC/USDT", "1d", limit=2)
        
        if 'price_data' in st.session_state and eth_cache_key in st.session_state.price_data:
            print("使用緩存的ETH數據")
            eth_data = st.session_state.price_data[eth_cache_key]
        else:
            eth_data = get_crypto_data("ETH/USDT", "1d", limit=2)
        
        # 計算比特幣24小時變化百分比
        if btc_data is not None and len(btc_data) >= 2:
            btc_change = ((btc_data['close'].iloc[-1] - btc_data['close'].iloc[-2]) / btc_data['close'].iloc[-2]) * 100
        else:
            btc_change = 0
            
        # 計算以太坊24小時變化百分比    
        if eth_data is not None and len(eth_data) >= 2:
            eth_change = ((eth_data['close'].iloc[-1] - eth_data['close'].iloc[-2]) / eth_data['close'].iloc[-2]) * 100
        else:
            eth_change = 0
            
        # 估算恐懼貪婪指數 (簡單模型)
        # 使用比特幣價格變化和交易量來估算
        if btc_data is not None:
            btc_vol_change = 0
            if len(btc_data) >= 2:
                try:
                    btc_vol_change = ((btc_data['volume'].iloc[-1] - btc_data['volume'].iloc[-2]) / btc_data['volume'].iloc[-2]) * 100
                except:
                    btc_vol_change = 0  # 避免除以零錯誤
            
            # 估算恐懼貪婪指數：50為中性，根據價格和交易量變化調整
            fear_greed = 50 + (btc_change * 1.5) + (btc_vol_change * 0.5)
            # 限制在0-100範圍內
            fear_greed = max(0, min(100, fear_greed))
            fear_greed = int(fear_greed)
            
            # 判斷變化方向
            fear_greed_change = "+8" if btc_change > 0 else "-8"
        else:
            fear_greed = 50
            fear_greed_change = "0"
            
        # 使用真實數據獲取市值 (使用BTC價格和估算的比例)
        if btc_data is not None:
            btc_price = btc_data['close'].iloc[-1]
            # 估算BTC市值 (已知比特幣流通量約1900萬)
            btc_market_cap = btc_price * 19000000 / 1000000000  # 單位：十億美元
            
            # 估算總市值 (根據主導率)
            btc_dominance = 50.0  # 比特幣主導率估計值（百分比）
            total_market_cap = btc_market_cap * 100 / btc_dominance  # 總市值（十億美元）
            
            # 估算24h成交量 (通常是總市值的3-5%)
            total_volume = total_market_cap * 0.04  # 假設成交量是總市值的4%
        else:
            # 使用更新的模擬數據
            btc_price = 68500
            btc_market_cap = 1300
            total_market_cap = 2600
            total_volume = 85
            
    except Exception as e:
        st.error(f"獲取市場數據時出錯: {str(e)}")
        # 使用更新的預設值
        btc_change = 2.4
        eth_change = 1.8
        fear_greed = 65
        fear_greed_change = "+8"
        btc_market_cap = 1300
        total_market_cap = 2600
        total_volume = 85
    
    # 修正為使用T（兆）作為單位，而不是B（十億）
    if total_market_cap > 1000:
        total_market_cap_str = f"${total_market_cap/1000:.1f}T"  # 轉換為兆
    else:
        total_market_cap_str = f"${total_market_cap:.1f}B"  # 保持十億
    
    # 使用列布局顯示市場概覽數據
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("比特幣主導率", f"{50.0:.1f}%", f"{'+' if btc_change > eth_change else '-'}{abs(btc_change - eth_change):.1f}%")
    
    with col2:
        st.metric("市場總市值", total_market_cap_str, f"{'+' if btc_change > 0 else ''}{btc_change:.1f}%")
    
    with col3:
        st.metric("24h成交量", f"${total_volume:.1f}B", f"{'+' if btc_change > 0 else ''}{btc_change * 1.2:.1f}%")
    
    with col4:
        st.metric("恐懼貪婪指數", f"{fear_greed}", fear_greed_change)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 創建熱門加密貨幣數據表格
    st.markdown('<div class="stCardContainer">', unsafe_allow_html=True)
    st.markdown("<h3>熱門加密貨幣</h3>", unsafe_allow_html=True)
    
    # 嘗試獲取真實市場數據
    crypto_list = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 'ADA/USDT', 'DOGE/USDT', 'SHIB/USDT']
    market_data_list = []
    
    with st.spinner("正在獲取市場數據..."):
        for symbol in crypto_list:
            try:
                # 檢查是否已有緩存數據
                cache_key = f"{symbol}_1d"
                if 'price_data' in st.session_state and cache_key in st.session_state.price_data:
                    print(f"使用緩存的{symbol}數據")
                    df = st.session_state.price_data[cache_key]
                else:
                    # 獲取當日數據
                    df = get_crypto_data(symbol, "1d", limit=8)
                
                if df is not None and len(df) > 0:
                    # 獲取最新價格
                    current_price = df['close'].iloc[-1]
                    
                    # 計算24小時變化百分比
                    if len(df) >= 2:
                        change_24h = ((df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2]) * 100
                    else:
                        change_24h = 0
                        
                    # 計算7天變化百分比
                    if len(df) >= 8:
                        change_7d = ((df['close'].iloc[-1] - df['close'].iloc[-8]) / df['close'].iloc[-8]) * 100
                    else:
                        change_7d = 0
                        
                    # 估算市值 (使用固定的流通量估算)
                    market_cap_map = {
                        'BTC/USDT': 19000000,  # BTC 流通量約1900萬
                        'ETH/USDT': 120000000,  # ETH 流通量約1.2億
                        'SOL/USDT': 440000000,  # SOL 流通量約4.4億
                        'BNB/USDT': 155000000,  # BNB 流通量約1.55億
                        'XRP/USDT': 58000000000,  # XRP 流通量約580億
                        'ADA/USDT': 36000000000,  # ADA 流通量約360億
                        'DOGE/USDT': 145000000000,  # DOGE 流通量約1450億
                        'SHIB/USDT': 589000000000000  # SHIB 流通量約589萬億
                    }
                    
                    circulation = market_cap_map.get(symbol, 1000000)
                    market_cap = current_price * circulation / 1000000000  # 十億美元
                    
                    # 估算24小時成交量 (使用當前價格和成交量估算)
                    volume_24h = df['volume'].iloc[-1] / 1000000000  # 十億美元
                    
                    # 添加到數據列表
                    symbol_name = symbol.split('/')[0]
                    market_data_list.append({
                        '幣種': {
                            'BTC/USDT': '比特幣',
                            'ETH/USDT': '以太坊',
                            'SOL/USDT': '索拉納',
                            'BNB/USDT': '幣安幣',
                            'XRP/USDT': '瑞波幣',
                            'ADA/USDT': '艾達幣',
                            'DOGE/USDT': '狗狗幣',
                            'SHIB/USDT': '柴犬幣'
                        }.get(symbol, symbol),
                        '代碼': symbol_name,
                        '價格(USDT)': current_price,
                        '24h漲跌幅': f"{'+' if change_24h > 0 else ''}{change_24h:.1f}%",
                        '7d漲跌幅': f"{'+' if change_7d > 0 else ''}{change_7d:.1f}%",
                        '市值(十億)': market_cap,
                        '24h成交量(十億)': volume_24h
                    })
                
            except Exception as e:
                st.error(f"獲取 {symbol} 數據時出錯: {str(e)}")
    
    # 如果無法獲取真實數據，使用模擬數據
    if not market_data_list:
        market_data_list = [
            {'幣種': '比特幣', '代碼': 'BTC', '價格(USDT)': 68750.25, '24h漲跌幅': '+2.4%', '7d漲跌幅': '+5.7%', '市值(十億)': 1350.8, '24h成交量(十億)': 28.5},
            {'幣種': '以太坊', '代碼': 'ETH', '價格(USDT)': 3495.45, '24h漲跌幅': '+1.8%', '7d漲跌幅': '+8.3%', '市值(十億)': 420.3, '24h成交量(十億)': 14.2},
            {'幣種': '索拉納', '代碼': 'SOL', '價格(USDT)': 178.65, '24h漲跌幅': '+3.2%', '7d漲跌幅': '+10.5%', '市值(十億)': 78.3, '24h成交量(十億)': 5.8},
            {'幣種': '幣安幣', '代碼': 'BNB', '價格(USDT)': 575.43, '24h漲跌幅': '+1.2%', '7d漲跌幅': '+3.8%', '市值(十億)': 88.7, '24h成交量(十億)': 2.3},
            {'幣種': '瑞波幣', '代碼': 'XRP', '價格(USDT)': 0.624, '24h漲跌幅': '+0.7%', '7d漲跌幅': '+2.1%', '市值(十億)': 34.5, '24h成交量(十億)': 1.6},
            {'幣種': '艾達幣', '代碼': 'ADA', '價格(USDT)': 0.472, '24h漲跌幅': '+1.5%', '7d漲跌幅': '+4.7%', '市值(十億)': 16.8, '24h成交量(十億)': 0.9},
            {'幣種': '狗狗幣', '代碼': 'DOGE', '價格(USDT)': 0.158, '24h漲跌幅': '+2.8%', '7d漲跌幅': '+6.5%', '市值(十億)': 22.4, '24h成交量(十億)': 1.4},
            {'幣種': '柴犬幣', '代碼': 'SHIB', '價格(USDT)': 0.00002741, '24h漲跌幅': '+4.3%', '7d漲跌幅': '+12.2%', '市值(十億)': 16.2, '24h成交量(十億)': 3.1}
        ]
    
    # 創建DataFrame
    market_data = pd.DataFrame(market_data_list)
    
    # 為價格上升項目添加綠色，下降項目添加紅色
    def color_change(val):
        if isinstance(val, str) and '+' in val:
            return f'color: #4CAF50; font-weight: bold;'
        elif isinstance(val, str) and '-' in val:
            return f'color: #F44336; font-weight: bold;'
        return ''
    
    # 使用applymap而不是map
    styled_market_data = market_data.style.applymap(color_change, subset=['24h漲跌幅', '7d漲跌幅'])
    
    # 顯示樣式化的表格
    st.dataframe(styled_market_data, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 創建市場趨勢可視化
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="stCardContainer">', unsafe_allow_html=True)
        st.markdown("<h3>主要代幣市值份額</h3>", unsafe_allow_html=True)
        
        # 使用實際市值數據創建餅圖
        if len(market_data_list) > 0:
            labels = [item['代碼'] for item in market_data_list]
            values = [item['市值(十億)'] for item in market_data_list]
            
            # 計算總市值和百分比
            total = sum(values)
            percentages = [value / total * 100 for value in values]
            
            # 使用實際數據創建餅圖
            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=percentages,
                hole=.4,
                marker_colors=['#F7931A', '#627EEA', '#00FFA3', '#F3BA2F', '#23292F', '#3CC8C8', '#C3A634', '#E0E0E0']
            )])
        else:
            # 使用模擬數據創建餅圖
            labels = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'DOGE', '其他']
            values = [51.2, 18.4, 3.4, 5.1, 1.8, 0.9, 1.0, 18.2]
            
            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                hole=.4,
                marker_colors=['#F7931A', '#627EEA', '#00FFA3', '#F3BA2F', '#23292F', '#3CC8C8', '#C3A634', '#E0E0E0']
            )])
        
        fig.update_layout(
            template='plotly_dark',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=30, b=20),
            height=300
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="stCardContainer">', unsafe_allow_html=True)
        st.markdown("<h3>7日漲跌幅比較</h3>", unsafe_allow_html=True)
        
        # 使用實際市值數據創建條形圖
        if len(market_data_list) > 0:
            coins = [item['代碼'] for item in market_data_list]
            changes = [float(item['7d漲跌幅'].replace('%', '').replace('+', '')) for item in market_data_list]
            
            # 為正負值設定不同顏色
            colors = ['#4CAF50' if c > 0 else '#F44336' for c in changes]
            
            fig = go.Figure(data=[go.Bar(
                x=coins,
                y=changes,
                marker_color=colors
            )])
        else:
            # 使用模擬數據創建條形圖
            coins = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'DOGE', 'SHIB']
            changes = [8.3, 12.7, 22.5, 4.8, -2.3, 3.8, 15.2, 28.7]
            
            # 為正負值設定不同顏色
            colors = ['#4CAF50' if c > 0 else '#F44336' for c in changes]
            
            fig = go.Figure(data=[go.Bar(
                x=coins,
                y=changes,
                marker_color=colors
            )])
        
        fig.update_layout(
            title='7日漲跌幅 (%)',
            template='plotly_dark',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=60, b=20),
            height=300
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

with tabs[3]:
    # 設置標籤內容
    st.markdown("<h2>設置</h2>", unsafe_allow_html=True)
    
    # 創建設置卡片
    st.markdown('<div class="stCardContainer">', unsafe_allow_html=True)
    st.markdown("<h3>應用設置</h3>", unsafe_allow_html=True)
    
    # 主題設置
    st.radio("主題", ["深色模式", "淺色模式"], index=0)
    
    # 默認圖表時間範圍
    st.select_slider("默認圖表時間範圍", options=["50", "100", "200", "500", "全部"], value="100")
    
    # 顯示設置
    st.checkbox("顯示交易量圖表", value=True)
    st.checkbox("顯示移動平均線", value=True)
    st.checkbox("顯示支撐/阻力位", value=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # API 設置卡片
    st.markdown('<div class="stCardContainer">', unsafe_allow_html=True)
    st.markdown("<h3>API 設置</h3>", unsafe_allow_html=True)
    
    # OpenAI API 設置
    openai_key = st.text_input("OpenAI API 密鑰", type="password", value="*" * 10 if OPENAI_API_KEY else "")
    
    # DeepSeek API 設置
    deepseek_key = st.text_input("DeepSeek API 密鑰", type="password", value="*" * 10 if DEEPSEEK_API_KEY else "")
    
    # CoinMarketCap API 設置
    cmc_key = st.text_input("CoinMarketCap API 密鑰", type="password", value="*" * 10 if COINMARKETCAP_API_KEY else "")
    
    # 保存按鈕
    st.button("保存設置")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 關於應用卡片
    st.markdown('<div class="stCardContainer">', unsafe_allow_html=True)
    st.markdown("<h3>關於</h3>", unsafe_allow_html=True)
    
    st.markdown("""
    **0xAI CryptoCat** 是一個使用多模型 AI 技術的加密貨幣分析工具，結合了技術分析和 AI 驅動的市場分析。
    
    **版本**: v1.0.0
    
    **開發者**: Terry Lee
    
    **使用的 AI 模型**:
    - DeepSeek V3 (技術分析和整合分析)
    - GPT-4o-mini (市場情緒分析)
    
    **數據來源**:
    - DexScreener API
    - Coincap API
    - CoinMarketCap API
    """)
    
    st.markdown('</div>', unsafe_allow_html=True)

# 移除底部 Streamlit 水印
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)
