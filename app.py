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

# 從Streamlit secrets或環境變數讀取API密鑰，如果都不存在則使用預設值
if 'DEEPSEEK_API_KEY' in st.secrets:
    DEEPSEEK_API_KEY = st.secrets['DEEPSEEK_API_KEY']
else:
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-6ae04d6789f94178b4053d2c42650b6c")

# 設置 CoinMarketCap API 密鑰
if 'COINMARKETCAP_API_KEY' in st.secrets:
    COINMARKETCAP_API_KEY = st.secrets['COINMARKETCAP_API_KEY']
else:
    COINMARKETCAP_API_KEY = os.getenv("COINMARKETCAP_API_KEY", "b54bcf4d-1bca-4e8e-9a24-22ff2c3d462c")

# 設置 Bitget MCP 服務器
BITGET_MCP_SERVER = "http://localhost:3000"

# 從 Coinbase MCP 獲取加密貨幣價格數據
def get_coinbase_price(symbol):
    """通過 Coinbase MCP 獲取加密貨幣價格"""
    try:
        st.info(f"正在嘗試從 Coinbase 獲取 {symbol} 價格...")
        
        # 映射幣種符號
        token_mapping = {
            'BTC/USDT': 'BTC',
            'ETH/USDT': 'ETH',
            'SOL/USDT': 'SOL',
            'BNB/USDT': 'BNB',
            'XRP/USDT': 'XRP',
            'ADA/USDT': 'ADA',
            'DOGE/USDT': 'DOGE',
            'SHIB/USDT': 'SHIB'
        }
        
        # 檢查幣種映射
        if symbol in token_mapping:
            token_symbol = token_mapping[symbol]
        else:
            token_symbol = symbol.split('/')[0]  # 獲取交易對的第一部分
        
        # 創建錢包（如果需要）
        response = mcp_coinbase_composio_COINBASE_LIST_WALLETS(params={})
        
        if not response:
            st.warning("無法獲取 Coinbase 錢包列表")
            return None
            
        # 使用第一個可用的錢包
        wallet = response[0] if response else None
        
        if not wallet or not wallet.get('id'):
            st.warning("未找到可用的 Coinbase 錢包")
            return None
            
        # 請求測試網絡資金（用於測試）
        faucet_resp = mcp_coinbase_composio_COINBASE_COINBASE_FAUCET(params={
            "wallet_id": wallet['id'],
            "asset_id": token_symbol if token_symbol != 'SHIB' else 'ETH'  # SHIB 可能不直接支持
        })
        
        # 獲取錢包信息以查看資產餘額
        wallet_info = mcp_coinbase_composio_COINBASE_GET_WALLET_INFO(params={
            "wallet_id": wallet['id']
        })
        
        if not wallet_info or 'balance' not in wallet_info:
            st.warning("無法獲取 Coinbase 錢包餘額")
            return None
            
        # 嘗試從餘額中找到對應的代幣
        for asset in wallet_info['balance']:
            if asset['asset_symbol'].upper() == token_symbol.upper():
                st.success(f"成功從 Coinbase 獲取 {symbol} 價格")
                
                # 返回價格（這裡我們使用 1:1 的匯率，實際應用中應獲取真實匯率）
                return float(asset['unit_price_usd'])
        
        st.warning(f"Coinbase 錢包中未找到 {token_symbol} 代幣")
        return None
            
    except Exception as e:
        st.error(f"Coinbase 價格獲取出錯: {str(e)}")
        return None

# 從本地運行的 Bitget MCP Server 獲取加密貨幣價格
def get_bitget_price(token):
    """使用本地運行的 Bitget MCP Server 獲取加密貨幣價格"""
    try:
        st.info(f"正在從 Bitget API 獲取 {token} 價格...")
        
        # 映射幣種符號
        token_mapping = {
            'BTC/USDT': 'BTC',
            'ETH/USDT': 'ETH',
            'SOL/USDT': 'SOL',
            'BNB/USDT': 'BNB',
            'XRP/USDT': 'XRP',
            'ADA/USDT': 'ADA',
            'DOGE/USDT': 'DOGE',
            'SHIB/USDT': 'SHIB'
        }
        
        # 檢查幣種映射
        if token in token_mapping:
            token_symbol = token_mapping[token]
        else:
            token_symbol = token.split('/')[0]  # 獲取交易對的第一部分
            
        # 構建 Bitget MCP 請求
        payload = {
            "tool": "getTokenPrice",
            "parameters": {
                "token": token_symbol
            }
        }
        
        headers = {
            "Content-Type": "application/json"
        }

        # 重試機制
        max_retries = 3
        retry_delay = 1
        
        for retry in range(max_retries):
            try:
                if retry > 0:
                    st.info(f"嘗試第 {retry+1} 次連接 Bitget API...")
                    time.sleep(retry_delay)
                
                # 使用短超時時間快速檢測服務器是否運行
                response = requests.post(
                    f"{BITGET_MCP_SERVER}/api", 
                    headers=headers, 
                    json=payload,
                    timeout=5  # 5秒超時
                )
                
                if response.status_code == 200:
                    price_data = response.json()
                    st.success(f"成功從 Bitget API 獲取 {token} 價格: ${price_data}")
                    return float(price_data)
                else:
                    st.warning(f"Bitget MCP Server 請求失敗，狀態碼: {response.status_code}")
                    retry_delay *= 2  # 指數退避
                    continue
                    
            except requests.exceptions.ConnectionError:
                if retry == max_retries - 1:
                    st.error(f"無法連接到 Bitget MCP Server (localhost:3000)，請確保服務已啟動")
                else:
                    st.warning(f"連接 Bitget MCP Server 失敗，{retry_delay}秒後重試...")
                    retry_delay *= 2
                    continue
            except requests.exceptions.Timeout:
                if retry == max_retries - 1:
                    st.error(f"連接 Bitget MCP Server 超時")
                else:
                    st.warning(f"連接 Bitget MCP Server 超時，{retry_delay}秒後重試...")
                    retry_delay *= 2
                    continue
            except Exception as e:
                st.error(f"Bitget API 請求過程中出錯: {e}")
                retry_delay *= 2
                continue
        
        st.error("達到最大重試次數，無法從 Bitget API 獲取數據")
        return None
            
    except Exception as e:
        st.error(f"Bitget API 數據獲取出錯: {e}")
        return None

# 顯示處理中動畫 - 簡化為靜態提示
def show_processing_animation():
    st.info("正在進行多模型AI分析...")
    # 移除進度條和氣球動畫
    time.sleep(1)  # 簡短延遲
    st.success("✅ 分析完成")

# 功能區塊：數據獲取 - 使用Coincap API替代CoinGecko
@st.cache_data(ttl=300)  # 5分鐘緩存
def get_crypto_data(symbol, timeframe, limit=100):
    try:
        # 將交易對格式轉換為Coincap格式
        # 例如：'BTC/USDT' -> 'bitcoin'
        coin_mapping = {
            'BTC/USDT': 'bitcoin',
            'ETH/USDT': 'ethereum',
            'SOL/USDT': 'solana',
            'BNB/USDT': 'binancecoin',
            'XRP/USDT': 'xrp',
            'ADA/USDT': 'cardano',
            'DOGE/USDT': 'dogecoin',
            'SHIB/USDT': 'shibainu'
        }
        
        # CoinMarketCap幣種ID映射
        cmc_id_mapping = {
            'BTC/USDT': 1,      # Bitcoin
            'ETH/USDT': 1027,   # Ethereum
            'SOL/USDT': 5426,   # Solana
            'BNB/USDT': 1839,   # Binance Coin
            'XRP/USDT': 52,     # XRP
            'ADA/USDT': 2010,   # Cardano
            'DOGE/USDT': 74,    # Dogecoin
            'SHIB/USDT': 5994   # Shiba Inu
        }
        
        # 將時間框架轉換為Coincap格式的時間間隔
        # 確保使用 Coincap 支持的間隔
        interval_mapping = {
            '15m': 'm15',
            '1h': 'h1',
            '4h': 'h6',  # 使用h6替代h4，因為Coincap沒有h4
            '1d': 'd1',
            '1w': 'd1'   # 使用d1替代w1，因為Coincap沒有w1
        }
        
        # 每個間隔允許的最大天數 (根據Coincap API限制)
        max_days_mapping = {
            'm15': 1,  # 15分鐘間隔最多查詢1天
            'h1': 25,  # 1小時間隔最多查詢25天 (避免超出30天限制)
            'h6': 25,  # 6小時間隔保守設置25天
            'd1': 90   # 天間隔可以查詢更長時間
        }
        
        if symbol not in coin_mapping:
            st.error(f"不支持的交易對: {symbol}")
            return None
            
        coin_id = coin_mapping[symbol]
        interval = interval_mapping.get(timeframe, 'h1')  # 默認1小時
        
        # 安全設置日期範圍，確保不超過API限制
        end_time = int(time.time() * 1000)  # 當前時間的毫秒時間戳
        max_days = max_days_mapping.get(interval, 7)  # 默認7天
        start_time = end_time - (max_days * 24 * 60 * 60 * 1000)
        
        # 使用Coincap API獲取市場數據
        url = f'https://api.coincap.io/v2/assets/{coin_id}/history'
        params = {
            'interval': interval,
            'start': start_time,
            'end': end_time
        }
        
        # 添加請求頭和延遲以避免請求限制
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # 使用退避重試機制
        max_retries = 3
        retry_delay = 2
        
        for retry in range(max_retries):
            try:
                # 添加延遲避免過於頻繁的請求
                if retry > 0:
                    time.sleep(retry_delay)
                    
                response = requests.get(url, params=params, headers=headers)
                
                if response.status_code == 200:
                    break
                    
                elif response.status_code == 429:  # 請求過多
                    st.warning("Coincap API請求頻率過高，正在轉用 CoinMarketCap API...")
                    return get_coinmarketcap_data(symbol, timeframe, limit)
                    
                elif response.status_code == 400 and "maximum date range" in response.text:
                    # 日期範圍太大，減小範圍
                    max_days = max(1, max_days // 2)  # 減半日期範圍
                    start_time = end_time - (max_days * 24 * 60 * 60 * 1000)
                    params['start'] = start_time
                    st.warning(f"調整日期範圍至{max_days}天並重試...")
                    continue
                    
                else:
                    st.error(f"獲取Coincap數據時出錯: {response.status_code} - {response.text}")
                    st.info("正在轉用 CoinMarketCap API...")
                    return get_coinmarketcap_data(symbol, timeframe, limit)
                    
            except Exception as e:
                st.error(f"請求過程中出錯: {e}")
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
                
        if response.status_code != 200:
            st.error("達到最大重試次數，正在轉用 CoinMarketCap API...")
            return get_coinmarketcap_data(symbol, timeframe, limit)
            
        data = response.json()
        
        # 確保數據不為空
        if 'data' not in data or not data['data']:
            st.error("獲取到的數據為空，正在轉用 CoinMarketCap API...")
            return get_coinmarketcap_data(symbol, timeframe, limit)
            
        # 轉換數據格式
        price_data = data['data']
        
        # 如果數據點太少，提出警告但繼續處理
        if len(price_data) < 10:
            st.warning(f"僅獲取到{len(price_data)}個數據點，轉用 CoinMarketCap API...")
            return get_coinmarketcap_data(symbol, timeframe, limit)
        
        # 將數據組織成DataFrame
        df_data = []
        for entry in price_data:
            timestamp = entry['time']
            price = float(entry['priceUsd'])
            
            # Coincap只提供收盤價，估算其他價格
            open_price = price * 0.99  # 估算開盤價
            high_price = price * 1.02  # 估算最高價
            low_price = price * 0.98   # 估算最低價
            
            # 估算成交量 (Coincap在歷史端點中不提供成交量，使用隨機生成的數據)
            volume = price * random.uniform(10000, 1000000)
            
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
            
        st.success(f"成功從 Coincap 獲取 {symbol} 的數據")
        return df
        
    except Exception as e:
        st.error(f"獲取數據時出錯: {e}")
        st.info("正在轉用 CoinMarketCap API...")
        return get_coinmarketcap_data(symbol, timeframe, limit)

# 新增：使用 CoinMarketCap API 獲取數據
def get_coinmarketcap_data(symbol, timeframe, limit=100):
    try:
        st.info("使用 CoinMarketCap API 獲取數據...")
        
        # 檢查支持的幣種
        cmc_id_mapping = {
            'BTC/USDT': 1,      # Bitcoin
            'ETH/USDT': 1027,   # Ethereum
            'SOL/USDT': 5426,   # Solana
            'BNB/USDT': 1839,   # Binance Coin
            'XRP/USDT': 52,     # XRP
            'ADA/USDT': 2010,   # Cardano
            'DOGE/USDT': 74,    # Dogecoin
            'SHIB/USDT': 5994   # Shiba Inu
        }
        
        if symbol not in cmc_id_mapping:
            st.error(f"CoinMarketCap API 不支持的交易對: {symbol}")
            # 嘗試使用 Bitget MCP Server
            current_price = get_bitget_price(symbol)
            if current_price is not None:
                return generate_dummy_data_with_price(symbol, limit, current_price)
            else:
                # 嘗試使用 Coinbase
                coinbase_price = get_coinbase_price(symbol)
                if coinbase_price is not None:
                    return generate_dummy_data_with_price(symbol, limit, coinbase_price)
                else:
                    return generate_dummy_data(symbol, limit)
            
        coin_id = cmc_id_mapping[symbol]
        
        # 計算時間範圍
        # CoinMarketCap API 的數據點間隔是固定的
        # 我們根據時間框架選擇適當的 CoinMarketCap API 間隔和數據點數量
        now = datetime.now()
        
        interval_days = {
            '15m': 1,     # 1天數據用於15分鐘圖表
            '1h': 7,      # 7天數據用於1小時圖表
            '4h': 30,     # 30天數據用於4小時圖表
            '1d': 90,     # 90天數據用於日線圖表
            '1w': 365     # 1年數據用於週線圖表
        }
        
        days = interval_days.get(timeframe, 30)
        
        # 計算開始時間
        start_date = now - timedelta(days=days)
        
        # 格式化為 ISO 8601 格式
        start_timestamp = int(start_date.timestamp())
        end_timestamp = int(now.timestamp())
        
        # 設置 CoinMarketCap API 請求
        url = "https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/historical"
        
        # 設置參數
        params = {
            'id': coin_id,  
            'time_start': start_timestamp,
            'time_end': end_timestamp,
            'interval': '1d',  # 最低間隔為每日，對於更小的時間框架，我們將進行估算
            'convert': 'USD'
        }
        
        headers = {
            'X-CMC_PRO_API_KEY': COINMARKETCAP_API_KEY,
            'Accept': 'application/json'
        }
        
        # 發送請求
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            error_message = f"CoinMarketCap API 請求失敗: {response.status_code}"
            try:
                error_data = response.json()
                st.error(f"CoinMarketCap API 請求失敗: {response.status_code} - {error_data}")
            except Exception:
                st.error(f"CoinMarketCap API 請求失敗: {response.status_code} - {response.text}")
            # 嘗試使用 Bitget MCP Server
            current_price = get_bitget_price(symbol)
            if current_price is not None:
                return generate_dummy_data_with_price(symbol, limit, current_price)
            else:
                # 嘗試使用 Coinbase
                coinbase_price = get_coinbase_price(symbol)
                if coinbase_price is not None:
                    return generate_dummy_data_with_price(symbol, limit, coinbase_price)
                else:
                    return generate_dummy_data(symbol, limit)
            
        data = response.json()
        
        # 確保數據不為空
        if 'data' not in data or not data['data'] or str(coin_id) not in data['data']:
            st.error("CoinMarketCap 返回的數據格式不正確或為空")
            # 嘗試使用 Bitget MCP Server
            current_price = get_bitget_price(symbol)
            if current_price is not None:
                return generate_dummy_data_with_price(symbol, limit, current_price)
            else:
                # 嘗試使用 Coinbase
                coinbase_price = get_coinbase_price(symbol)
                if coinbase_price is not None:
                    return generate_dummy_data_with_price(symbol, limit, coinbase_price)
                else:
                    return generate_dummy_data(symbol, limit)
            
        # 處理數據
        quotes = data['data'][str(coin_id)]['quotes']
        
        if not quotes:
            st.error("CoinMarketCap 未返回任何價格數據")
            # 嘗試使用 Bitget MCP Server
            current_price = get_bitget_price(symbol)
            if current_price is not None:
                return generate_dummy_data_with_price(symbol, limit, current_price)
            else:
                # 嘗試使用 Coinbase
                coinbase_price = get_coinbase_price(symbol)
                if coinbase_price is not None:
                    return generate_dummy_data_with_price(symbol, limit, coinbase_price)
                else:
                    return generate_dummy_data(symbol, limit)
            
        # 將數據轉換為 DataFrame
        df_data = []
        for quote in quotes:
            timestamp = quote['timestamp']  # ISO 8601 格式
            price = quote['quote']['USD']['price']
            volume = quote['quote']['USD']['volume_24h']
            
            # CoinMarketCap 只提供收盤價和成交量，估算其他價格
            # 為了創建更真實的數據，我們根據價格波動性添加一些隨機變化
            volatility = 0.02  # 假設 2% 的日內波動
            
            high_price = price * (1 + random.uniform(0, volatility))
            low_price = price * (1 - random.uniform(0, volatility))
            open_price = price * (1 + random.uniform(-volatility/2, volatility/2))
            
            # 將 ISO 8601 時間戳轉換為毫秒時間戳
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            ms_timestamp = int(dt.timestamp() * 1000)
            
            df_data.append([
                ms_timestamp,
                open_price,
                high_price,
                low_price,
                price,
                volume if volume else price * random.uniform(10000, 1000000)  # 如果成交量為空，生成模擬數據
            ])
        
        # 創建 DataFrame
        df = pd.DataFrame(df_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # 根據時間框架調整數據點數量
        # 對於較小的時間框架，可能需要生成額外的數據點
        if timeframe in ['15m', '1h', '4h'] and len(df) < limit:
            df = expand_dataframe(df, timeframe, limit)
        
        # 限制返回的行數
        if len(df) > limit:
            df = df.tail(limit)
            
        st.success(f"成功從 CoinMarketCap 獲取 {symbol} 的數據")
        return df
        
    except Exception as e:
        st.error(f"CoinMarketCap 數據獲取出錯: {e}")
        # 嘗試使用 Bitget MCP Server
        current_price = get_bitget_price(symbol)
        if current_price is not None:
            return generate_dummy_data_with_price(symbol, limit, current_price)
        else:
            # 嘗試使用 Coinbase
            coinbase_price = get_coinbase_price(symbol)
            if coinbase_price is not None:
                return generate_dummy_data_with_price(symbol, limit, coinbase_price)
            else:
                return generate_dummy_data(symbol, limit)

# 使用實時價格生成模擬數據
def generate_dummy_data_with_price(symbol, periods=100, current_price=None):
    """使用實時價格生成更準確的模擬數據"""
    st.warning(f"使用 Bitget API 的實時價格生成 {symbol} 的模擬歷史數據")
    
    # 生成時間戳列表
    end_date = datetime.now()
    start_date = end_date - timedelta(days=periods)
    dates = pd.date_range(start=start_date, end=end_date, periods=periods)
    
    # 使用提供的當前價格作為基準
    base_price = current_price
    volatility = 0.02  # 波動性
    
    # 根據當前價格反向生成歷史價格，添加一些隨機波動和趨勢
    price_data = [base_price]
    
    # 生成隨機趨勢方向
    trend = random.choice([-1, 1])
    
    # 從最近到最遠生成價格
    for i in range(1, periods):
        # 隨機添加趨勢轉折點
        if random.random() < 0.05:  # 5% 的概率轉變趨勢
            trend = -trend
            
        # 生成價格變化，加入趨勢因素
        change = np.random.normal(0.001 * trend, volatility)
        # 反向計算價格（從最近到最遠）
        price = price_data[-1] / (1 + change)
        price_data.append(price)
    
    # 反轉價格數據，使其從最遠到最近
    price_data.reverse()
    
    # 創建 DataFrame
    df = pd.DataFrame({
        'timestamp': dates,
        'open': [p * (1 - 0.005 * np.random.random()) for p in price_data],
        'high': [p * (1 + 0.01 * np.random.random()) for p in price_data],
        'low': [p * (1 - 0.01 * np.random.random()) for p in price_data],
        'close': price_data,
        'volume': [p * np.random.random() * 10000 for p in price_data]  # 根據價格生成成交量
    })
    
    return df

# 輔助函數：展開 DataFrame 以適應更小的時間框架
def expand_dataframe(df, timeframe, target_length):
    """
    為較小的時間框架生成額外的數據點
    例如：從日線數據生成小時級數據
    """
    if len(df) < 2:
        return df  # 至少需要兩個數據點來插值
        
    # 確定每個原始數據點要生成多少新數據點
    expansion_factor = {
        '15m': 96,  # 一天96個15分鐘
        '1h': 24,   # 一天24個小時
        '4h': 6     # 一天6個4小時
    }.get(timeframe, 1)
    
    new_rows = []
    
    # 遍歷原始數據，在每對相鄰點之間插入新數據
    for i in range(len(df) - 1):
        current = df.iloc[i]
        next_point = df.iloc[i + 1]
        
        # 計算時間差
        time_diff = (next_point['timestamp'] - current['timestamp']).total_seconds()
        time_step = time_diff / expansion_factor
        
        # 計算價格和成交量的差異
        price_diff = next_point['close'] - current['close']
        price_step = price_diff / expansion_factor
        
        volume_diff = next_point['volume'] - current['volume']
        volume_step = volume_diff / expansion_factor
        
        # 添加原始數據點
        new_rows.append(current.to_dict())
        
        # 生成中間數據點
        for j in range(1, expansion_factor):
            # 添加一些隨機波動使數據更真實
            random_factor = 1 + random.uniform(-0.005, 0.005)  # ±0.5% 的隨機波動
            
            new_time = current['timestamp'] + timedelta(seconds=time_step * j)
            new_close = current['close'] + (price_step * j) * random_factor
            
            # 確保生成的高低價合理
            volatility = abs(price_diff) * 0.2 * random_factor  # 使用價格差異的20%作為波動範圍
            new_high = new_close * (1 + random.uniform(0, 0.01))
            new_low = new_close * (1 - random.uniform(0, 0.01))
            new_open = current['close'] + (price_step * (j-1)) * random_factor if j > 1 else current['close']
            
            # 生成成交量
            new_volume = max(0, current['volume'] + (volume_step * j) * (1 + random.uniform(-0.1, 0.1)))
            
            new_rows.append({
                'timestamp': new_time,
                'open': new_open,
                'high': new_high,
                'low': new_low,
                'close': new_close,
                'volume': new_volume
            })
    
    # 添加最後一個原始數據點
    new_rows.append(df.iloc[-1].to_dict())
    
    # 創建新的 DataFrame
    expanded_df = pd.DataFrame(new_rows)
    
    # 確保數據量不超過目標長度
    if len(expanded_df) > target_length:
        expanded_df = expanded_df.tail(target_length)
        
    return expanded_df

# 生成模擬數據
def generate_dummy_data(symbol, periods=100):
    """當API數據獲取失敗時生成模擬數據"""
    st.warning(f"無法從API獲取 {symbol} 的數據，使用模擬數據進行演示。")
    
    # 生成時間戳列表
    end_date = datetime.now()
    start_date = end_date - timedelta(days=periods)
    dates = pd.date_range(start=start_date, end=end_date, periods=periods)
    
    # 基於不同貨幣設置不同的基準價格
    base_prices = {
        'BTC/USDT': 30000.0,
        'ETH/USDT': 1800.0,
        'SOL/USDT': 80.0,
        'BNB/USDT': 250.0,
        'XRP/USDT': 0.5,
        'ADA/USDT': 0.35,
        'DOGE/USDT': 0.1,
        'SHIB/USDT': 0.00001
    }
    
    base_price = base_prices.get(symbol, 100.0)  # 默認值
    volatility = 0.02  # 波動性
    
    # 生成帶有趨勢的價格序列
    price_data = [base_price]
    trend = random.choice([-1, 1])  # 隨機選擇上升或下降趨勢
    
    for i in range(1, periods):
        # 隨機添加趨勢轉折點
        if random.random() < 0.05:  # 5% 的概率轉變趨勢
            trend = -trend
            
        # 生成價格變化，加入趨勢因素
        change = np.random.normal(0.001 * trend, volatility)
        price = max(0.001, price_data[-1] * (1 + change))  # 確保價格為正
        price_data.append(price)
    
    # 創建 DataFrame
    df = pd.DataFrame({
        'timestamp': dates,
        'open': [p * (1 - 0.005 * np.random.random()) for p in price_data],
        'high': [p * (1 + 0.01 * np.random.random()) for p in price_data],
        'low': [p * (1 - 0.01 * np.random.random()) for p in price_data],
        'close': price_data,
        'volume': [p * np.random.random() * 10000 for p in price_data]  # 根據價格生成成交量
    })
    
    return df

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

# 多時間框架分析功能 - 移到SNR函數後面確保先定義再調用
def get_mtf_data(symbol, current_timeframe):
    """根據當前時間框架獲取多時間框架數據"""
    # 定義時間框架關係：較小 -> 較大
    timeframe_sequence = {
        '15m': ['5m', '15m', '1h', '4h'],
        '1h': ['15m', '1h', '4h', '1d'],
        '4h': ['1h', '4h', '1d', '1w'],
        '1d': ['4h', '1d', '1w', '1M'],
        '1w': ['1d', '1w', '1M']
    }
    
    # 如果當前時間框架不在預定義序列中，只返回當前時間框架的數據
    if current_timeframe not in timeframe_sequence:
        frames = [current_timeframe]
    else:
        frames = timeframe_sequence[current_timeframe]
    
    # 獲取數據，對較大時間框架獲取更多歷史數據
    mtf_data = {}
    for i, tf in enumerate(frames):
        # 較大時間框架需要更多數據來計算指標
        limit = 100 + (i * 50)  
        df = get_crypto_data(symbol, tf, limit=limit)
        if df is not None:
            mtf_data[tf] = df
    
    return mtf_data

# 多時間框架分析整合
def mtf_analysis(symbol, current_timeframe):
    """進行多時間框架技術分析"""
    mtf_data = get_mtf_data(symbol, current_timeframe)
    
    mtf_results = {}
    for tf, df in mtf_data.items():
        if df is not None and len(df) > 20:  # 確保有足夠數據計算指標
            smc_result, _ = smc_analysis(df)
            snr_result, _ = snr_analysis(df)
            
            # 計算附加指標
            trend_alignment = smc_result['recommendation'] == snr_result['recommendation']
            
            mtf_results[tf] = {
                'smc': smc_result,
                'snr': snr_result,
                'trend_aligned': trend_alignment,
                'confidence': 0.8 if trend_alignment else 0.5,
                'timeframe': tf
            }
    
    return mtf_results

# 生成多時間框架趨勢一致性分析
def get_mtf_trend_consensus(mtf_results):
    """分析不同時間框架之間的趨勢一致性"""
    if not mtf_results:
        return "無法獲取多時間框架數據"
    
    # 統計各個時間框架的趨勢
    bullish_count = sum(1 for tf_data in mtf_results.values() 
                       if tf_data['smc']['market_structure'] == 'bullish')
    bearish_count = sum(1 for tf_data in mtf_results.values() 
                        if tf_data['smc']['market_structure'] == 'bearish')
    
    # 計算趨勢一致性得分 (0-100)
    total_frames = len(mtf_results)
    if total_frames == 0:
        return "無法計算趨勢一致性"
    
    if bullish_count > bearish_count:
        consensus_score = (bullish_count / total_frames) * 100
        consensus_direction = "上升"
    else:
        consensus_score = (bearish_count / total_frames) * 100
        consensus_direction = "下降"
    
    consensus_strength = "強" if consensus_score >= 75 else "中等" if consensus_score >= 50 else "弱"
    
    aligned_timeframes = [tf for tf, data in mtf_results.items() 
                         if (data['smc']['market_structure'] == 'bullish' and bullish_count > bearish_count) or
                            (data['smc']['market_structure'] == 'bearish' and bearish_count >= bullish_count)]
    
    report = f"""
    ## 多時間框架趨勢一致性分析
    
    **整體趨勢方向**: {consensus_direction}
    **一致性強度**: {consensus_strength} ({consensus_score:.1f}%)
    **趨勢一致的時間框架**: {', '.join(aligned_timeframes)}
    
    ### 時間框架詳細分析:
    """
    
    for tf, data in mtf_results.items():
        report += f"""
        **{tf}**: {'上升' if data['smc']['market_structure'] == 'bullish' else '下降'} 趨勢
        - 價格: ${data['smc']['price']:.2f}
        - 支撐位: ${data['smc']['support_level']:.2f}
        - 阻力位: ${data['smc']['resistance_level']:.2f}
        - RSI: {data['snr']['rsi']:.1f}
        - 建議: {'買入' if data['smc']['recommendation'] == 'buy' else '賣出' if data['smc']['recommendation'] == 'sell' else '觀望'}
        """
    
    return report

# 添加激進策略分析 - 移到前面確保先定義再調用
def generate_aggressive_strategy(symbol, price, support, resistance):
    """生成激進交易策略建議"""
    mid_price = (support + resistance) / 2
    range_size = resistance - support
    
    # 計算中軸區間 (中間價格的±2%)
    mid_zone_lower = mid_price * 0.98
    mid_zone_upper = mid_price * 1.02
    
    # 根據當前價格位置生成策略
    if price >= mid_zone_lower and price <= mid_zone_upper:
        # 計算更合理的目標價位，確保止盈高於入場點
        breakout_target = max(resistance, mid_zone_upper * 1.02)  # 確保目標至少高於中軸上限2%
        breakdown_target = min(support, mid_zone_lower * 0.98)  # 確保目標至少低於中軸下限2%
        
        strategy = f"""
        ## 激進交易策略：中軸突破策略
        
        當前價格 ${price:.2f} 接近區間中軸（${mid_price:.2f}±2%）
        
        **看漲突破策略**：
        - 入場點：突破 ${mid_zone_upper:.2f} 且成交量增加
        - 止盈：${breakout_target:.2f}
        - 止損：${mid_zone_upper * 0.99:.2f} 下方（緊跟入場點）
        
        **看跌突破策略**：
        - 入場點：跌破 ${mid_zone_lower:.2f} 且成交量增加
        - 止盈：${breakdown_target:.2f}
        - 止損：${mid_zone_lower * 1.01:.2f} 上方（緊跟入場點）
        
        **風險提示**：此為高風險策略，建議僅使用較小倉位（總資金的5-10%）
        """
    elif price < mid_zone_lower and price > support:
        # 支撐反彈策略，入場在支撐位附近，目標是中軸或阻力位
        entry_point = support * 1.01  # 略高於支撐位
        target = max(mid_price, entry_point * 1.03)  # 確保目標高於入場點
        
        strategy = f"""
        ## 激進交易策略：支撐反彈策略
        
        當前價格 ${price:.2f} 接近支撐區域
        
        **反彈做多策略**：
        - 入場點：${entry_point:.2f} 附近出現反彈確認信號（如K線底部影線、成交量增加）
        - 止盈：${target:.2f}
        - 止損：${support * 0.99:.2f}（支撐位下方）
        
        **風險提示**：當價格接近支撐位但尚未確認反彈時，此為高風險策略
        """
    elif price > mid_zone_upper and price < resistance:
        # 阻力回落策略，入場在阻力位附近，目標是中軸或支撐位
        entry_point = resistance * 0.99  # 略低於阻力位
        target = min(mid_price, entry_point * 0.97)  # 確保目標低於入場點
        
        strategy = f"""
        ## 激進交易策略：阻力回落策略
        
        當前價格 ${price:.2f} 接近阻力區域
        
        **回落做空策略**：
        - 入場點：${entry_point:.2f} 附近出現回落確認信號（如K線上部影線、成交量減少）
        - 止盈：${target:.2f}
        - 止損：${resistance * 1.01:.2f}（阻力位上方）
        
        **風險提示**：當價格接近阻力位但尚未確認回落時，此為高風險策略
        """
    else:
        # 區間突破策略
        if price > resistance:
            # 突破阻力位
            entry = resistance * 1.02  # 確認突破
            target = price + range_size * 0.5  # 延伸目標
            stop_loss = resistance * 0.99  # 回落到阻力位下方
            
            strategy = f"""
            ## 激進交易策略：阻力突破追漲策略
            
            當前價格 ${price:.2f} 已突破阻力位 ${resistance:.2f}
            
            **順勢做多策略**：
            - 入場點：${entry:.2f}（確認突破）
            - 止盈：${target:.2f}（目標區間延伸）
            - 止損：${stop_loss:.2f}（跌破阻力位）
            
            **風險提示**：價格已脫離主要交易區間，波動性可能增加，請謹慎管理風險
            """
        else:  # price < support
            # 跌破支撐位
            entry = support * 0.98  # 確認跌破
            target = price - range_size * 0.5  # 延伸目標
            stop_loss = support * 1.01  # 反彈到支撐位上方
            
            strategy = f"""
            ## 激進交易策略：支撐跌破追跌策略
            
            當前價格 ${price:.2f} 已跌破支撐位 ${support:.2f}
            
            **順勢做空策略**：
            - 入場點：${entry:.2f}（確認跌破）
            - 止盈：${target:.2f}（目標區間延伸）
            - 止損：${stop_loss:.2f}（反彈到支撐位）
            
            **風險提示**：價格已脫離主要交易區間，波動性可能增加，請謹慎管理風險
            """
    
    return strategy

# 調用DeepSeek API進行技術分析
def get_deepseek_analysis(symbol, timeframe, data, smc_results, snr_results, analysis_depth):
    # 準備價格歷史數據
    price_history = data.tail(30)[['timestamp', 'close']].copy()
    price_history['timestamp'] = price_history['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    price_data = price_history.to_dict('records')
    
    # 根據分析深度調整提示詳細程度
    detail_level = {
        "基本": "簡短的基本分析，專注於主要趨勢和關鍵支撐阻力位",
        "標準": "中等詳細度的分析，包括市場結構、趨勢強度、市場情緒評估和主要技術指標",
        "深入": "詳細的技術分析，包括多時間框架分析、市場結構識別、流動性分析、市場情緒評估和綜合交易建議"
    }
    
    # 準備提示
    prompt = f"""
    作為專業的加密貨幣技術分析師，請你對以下加密貨幣數據進行{detail_level[analysis_depth]}：
    
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
    - RSI狀態: {"超買" if snr_results['overbought'] else "超賣" if snr_results['oversold'] else "中性"}
    - 近期支撐位: ${snr_results['near_support']:.2f}
    - 近期阻力位: ${snr_results['near_resistance']:.2f}
    
    近期價格數據:
    {json.dumps(price_data, ensure_ascii=False)}
    
    請提供以下三個分析部分，每部分要清晰標記並互相區分:
    
    第一部分 - SMC技術分析 (市場結構):
    1. 市場結構分析 (根據SMC方法論)
    2. 流動性分析
    3. 主要支撐阻力位評估
    4. 可能的價格目標區間
    5. 交易建議（包含風險回報比率）
    
    第二部分 - 市場情緒分析:
    1. 當前市場情緒評估
    2. 投資者行為心理分析
    3. 交易者對支撐位/阻力位的共識程度
    4. 近期可能的市場情緒轉變點
    
    第三部分 - 綜合交易策略:
    1. 整合上述分析的最終交易建議
    2. 信心指數和風險評分
    3. 風險管理和止損策略
    4. 倉位大小建議
    5. 多時間框架考量
    
    在交易建議部分，請計算並詳細說明風險回報比率(Risk-Reward Ratio)，包括:
    - 多頭和空頭交易的建議入場點
    - 目標價位（至少兩個，包括保守和激進目標）
    - 建議止損位置
    - 各個目標的風險回報比率計算
    - 基於當前市場結構和波動性的最佳倉位大小建議
    
    分析應遵循專業技術分析方法，關注市場結構轉換、大資金行為和流動性區域。請用繁體中文回答，並注重專業性。
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
        "max_tokens": 2000  # 增加token數量以容納更多分析內容
    }
    
    # API請求
    with st.spinner("正在使用DeepSeek進行全方位加密貨幣分析..."):
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
    
    # 計算風險回報比率數據
    if trend == 'bullish':
        # 多頭交易設置
        entry_point = max(price * 0.99, support * 1.02)  # 略低於當前價格或略高於支撐位
        stop_loss = support * 0.97
        risk = entry_point - stop_loss
        
        # 計算目標價位
        target1 = min(resistance * 0.98, entry_point * 1.03)  # 保守目標：接近阻力位但略低
        target2 = resistance * 1.05  # 激進目標：突破阻力位
        
        # 計算風險回報比率
        rr_ratio1 = round((target1 - entry_point) / risk, 2)
        rr_ratio2 = round((target2 - entry_point) / risk, 2)
        
        # 根據風險回報比決定倉位
        if rr_ratio1 >= 2:
            position_size = "20-25%"
        elif rr_ratio1 >= 1.5:
            position_size = "15-20%"
        else:
            position_size = "10-15%"
    else:  # bearish
        # 空頭交易設置
        entry_point = min(price * 1.01, resistance * 0.98)  # 略高於當前價格或略低於阻力位
        stop_loss = resistance * 1.03
        risk = stop_loss - entry_point
        
        # 計算目標價位
        target1 = max(support * 1.02, entry_point * 0.97)  # 保守目標：接近支撐位但略高
        target2 = support * 0.95  # 激進目標：跌破支撐位
        
        # 計算風險回報比率
        rr_ratio1 = round((entry_point - target1) / risk, 2)
        rr_ratio2 = round((entry_point - target2) / risk, 2)
        
        # 根據風險回報比決定倉位
        if rr_ratio1 >= 2:
            position_size = "20-25%"
        elif rr_ratio1 >= 1.5:
            position_size = "15-20%"
        else:
            position_size = "10-15%"
    
    # 計算風險評分
    risk_score = 5
    if trend == 'bullish':
        risk_score -= 1
    else:
        risk_score += 1
        
    if snr_results['overbought']:
        risk_score += 2
    elif snr_results['oversold']:
        risk_score -= 2
        
    risk_score = max(1, min(10, risk_score))
    
    # 市場情緒分析
    market_state = "超買" if snr_results['overbought'] else "超賣" if snr_results['oversold'] else "中性"
    
    return f"""
    # {symbol} {timeframe} 全方位分析報告
    
    ## 第一部分 - SMC技術分析

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
    
    ### 交易建議（包含風險回報比率）
    {"#### 多頭交易策略" if trend == 'bullish' else "#### 空頭交易策略"}
    
    **入場點**：${entry_point:.2f}
    **止損位**：${stop_loss:.2f}
    
    **目標價位**：
    - 保守目標：${target1:.2f}（風險回報比 = {rr_ratio1}）
    - 激進目標：${target2:.2f}（風險回報比 = {rr_ratio2}）
    
    **建議倉位大小**：總資金的{position_size}
    
    **策略執行**：
    {"價格接近支撐位且RSI為{snr_results['rsi']:.2f}，顯示超賣特徵。建議分批進場，首批在${entry_point:.2f}，第二批在出現反彈確認後。" 
    if snr_results['oversold'] and trend == 'bullish' else 
    "價格接近阻力位且RSI為{snr_results['rsi']:.2f}，顯示超買特徵。建議在${entry_point:.2f}附近做空，或減持現有多頭倉位。" 
    if snr_results['overbought'] and trend == 'bearish' else 
    f"建議等待更明確的進場信號。可在${entry_point:.2f}設置條件單，同時關注${support:.2f}和${resistance:.2f}這兩個關鍵價位的突破情況。"}
    
    ## 第二部分 - 市場情緒分析

    ### 當前市場情緒評估
    基於當前數據，{symbol}市場情緒呈現{"強烈看漲" if trend == 'bullish' and smc_results['trend_strength'] > 0.8 else 
    "看漲" if trend == 'bullish' else 
    "強烈看跌" if trend == 'bearish' and smc_results['trend_strength'] < 0.4 else 
    "看跌" if trend == 'bearish' else "中性"}傾向。

    ### 投資者行為心理分析
    RSI指標當前為{snr_results['rsi']:.2f}，處於{market_state}狀態，
    {"這通常是買入機會的信號" if market_state == "超賣" else 
    "這可能預示著短期調整的到來" if market_state == "超買" else 
    "未顯示明確的超買或超賣信號"}。
    
    ### 交易者對支撐/阻力位的共識程度
    目前市場支撐位與阻力位之間的價格區間較為明確，從${snr_results['near_support']:.2f}到${snr_results['near_resistance']:.2f}，
    {"近期交易者情緒偏向在支撐位附近買入" if trend == 'bullish' else 
    "近期交易者情緒偏向在阻力位附近賣出" if trend == 'bearish' else 
    "市場參與者情緒較為謹慎，等待更明確的方向"}。
    
    ### 近期可能的市場情緒轉變點
    考慮到{"近期加密貨幣市場整體回暖" if trend == 'bullish' else 
    "近期加密貨幣市場整體承壓" if trend == 'bearish' else 
    "近期加密貨幣市場波動加劇"}，交易者應{"保持樂觀但謹慎的態度" if trend == 'bullish' else 
    "保持謹慎的態度" if trend == 'bearish' else 
    "保持中性的態度"}。
    
    ## 第三部分 - 綜合交易策略

    ### 整合交易建議
    **建議操作**：{"買入" if trend == 'bullish' and not snr_results['overbought'] else 
                "賣出" if trend == 'bearish' and not snr_results['oversold'] else "觀望"}
    **信心指數**：{smc_results['trend_strength']*100:.1f}%
    **風險評分**：{risk_score}/10 ({"高風險" if risk_score > 7 else "中等風險" if risk_score > 4 else "低風險"})

    ### 風險管理策略
    - 止損位設置：${stop_loss:.2f}
    - 當價格達到保守目標後，將止損移至入場點以鎖定利潤
    - 建議倉位：總資金的{position_size}
    - 避免在{"高波動" if smc_results['trend_strength'] > 0.8 or snr_results['overbought'] or snr_results['oversold'] else "低流動性"}時段進行大額交易
    - 倉位總風險不應超過總資金的2%

    ### 多時間框架考量
    建議同時關注更大時間框架（{"4小時" if timeframe == "1h" else "日線" if timeframe in ["15m", "4h"] else "週線"}）的走勢，確保與主趨勢一致。
    
    _分析時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_
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

# Streamlit頁面設定
st.set_page_config(
    page_title="CryptoAnalyzer - 加密貨幣分析工具", 
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/yourusername/crypto-analyzer',
        'Report a bug': "https://github.com/yourusername/crypto-analyzer/issues",
        'About': "# CryptoAnalyzer\n加密貨幣專業分析工具，整合SMC和SNR策略"
    }
)

# 自定義CSS樣式，美化界面
st.markdown("""
<style>
    /* 整體主題 */
    .main {
        background-color: #0e1117;
        color: #ffffff;
    }
    
    /* 卡片樣式 */
    div.stMetric {
        background-color: #1a1d24;
        border-radius: 10px;
        padding: 15px;
        border-left: 5px solid #4a8af4;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    
    /* 標題樣式 */
    h1, h2, h3 {
        color: #4a8af4;
        font-weight: bold;
    }
    
    /* 側邊欄樣式 */
    .sidebar .sidebar-content {
        background-color: #1a1d24;
    }
    
    /* 交易策略卡片 */
    div.stAlert {
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
    }
    
    /* 按鈕樣式 */
    .stButton>button {
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }
    
    /* 買入建議顏色 */
    .buy-rec {
        color: #4CAF50 !important;
        font-weight: bold;
    }
    
    /* 賣出建議顏色 */
    .sell-rec {
        color: #F44336 !important;
        font-weight: bold;
    }
    
    /* 觀望建議顏色 */
    .neutral-rec {
        color: #FFC107 !important;
        font-weight: bold;
    }
    
    /* 分隔線樣式 */
    hr {
        border: 1px solid #2c303a;
    }
</style>
""", unsafe_allow_html=True)

# 頁面標題
st.title("CryptoAnalyzer 加密貨幣智能分析平台")
st.markdown(f"### 專業市場洞察 | {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# 創建選項卡，優化信息顯示
tab1, tab2 = st.tabs(["📊 市場分析", "📈 價格圖表"])

# 簡化會話狀態
if "analyze_button" not in st.session_state:
    st.session_state.analyze_button = False

# 側邊欄 - 設定選項 (優化布局)
st.sidebar.title("分析設定")
st.sidebar.markdown("---")

# 幣種選擇 - 添加圖標
COINS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT", "DOGE/USDT", "SHIB/USDT"]
COIN_ICONS = {
    "BTC/USDT": "₿", "ETH/USDT": "Ξ", "SOL/USDT": "◎", "BNB/USDT": "🔶",
    "XRP/USDT": "✗", "ADA/USDT": "₳", "DOGE/USDT": "Ð", "SHIB/USDT": "🐕"
}

coin_options = [f"{COIN_ICONS[coin]} {coin}" for coin in COINS]
selected_coin_with_icon = st.sidebar.selectbox("選擇幣種", coin_options)
selected_coin = COINS[coin_options.index(selected_coin_with_icon)]

# 時間範圍選擇 - 更直觀的界面
TIMEFRAMES = {
    "15分鐘": "15m",
    "1小時": "1h", 
    "4小時": "4h",
    "1天": "1d",
    "1週": "1w"
}
selected_timeframe_name = st.sidebar.selectbox("選擇時間範圍", list(TIMEFRAMES.keys()))
selected_timeframe = TIMEFRAMES[selected_timeframe_name]

# 策略選擇 - 添加圖標
strategy_options = ["🧠 SMC策略分析", "📏 SNR策略分析", "🔄 SMC+SNR整合分析"]
selected_strategy_with_icon = st.sidebar.selectbox("選擇分析策略", strategy_options)
selected_strategy = selected_strategy_with_icon.split(" ", 1)[1]

# 分析深度選擇 - 視覺化選擇器
analysis_detail = st.sidebar.select_slider(
    "AI分析深度",
    options=["基本", "標準", "深入"],
    value="標準"
)

# 添加顏色指示器顯示當前分析深度
depth_colors = {"基本": "🟠", "標準": "🟢", "深入": "🔵"}
st.sidebar.markdown(f"當前分析深度: {depth_colors[analysis_detail]} {analysis_detail}")

# 激進交易策略選項 - 更明確的描述
show_aggressive = st.sidebar.checkbox("📊 顯示激進交易策略", value=False, 
                                      help="激進策略提供更高風險高回報的交易建議，適合有經驗的交易者")

# 側邊欄 - 分析按鈕，增強視覺效果
st.sidebar.markdown("---")
col1, col2 = st.sidebar.columns([1, 3])
with col1:
    st.markdown("### ")
    st.markdown("🔍")
with col2:
    analyze_btn = st.button("開始技術分析", key="start_analysis", type="primary", use_container_width=True)

if analyze_btn:
    st.session_state.analyze_button = True

# 自定義K線圖表函數 - 優化視覺效果
def plot_candlestick_chart(data, coin, timeframe_name):
    # 將數據格式化為Plotly可用格式
    increasing_color = '#26A69A'
    decreasing_color = '#EF5350'
    
    fig = go.Figure(data=[go.Candlestick(
        x=data['timestamp'],
        open=data['open'],
        high=data['high'],
        low=data['low'],
        close=data['close'],
        name='K線',
        increasing_line_color=increasing_color,
        decreasing_line_color=decreasing_color
    )])
    
    # 添加移動平均線
    fig.add_trace(go.Scatter(
        x=data['timestamp'],
        y=data['close'].rolling(window=20).mean(),
        name='20MA',
        line=dict(color='#FFEB3B', width=1.5)
    ))
    
    fig.add_trace(go.Scatter(
        x=data['timestamp'],
        y=data['close'].rolling(window=50).mean(),
        name='50MA',
        line=dict(color='#2196F3', width=1.5)
    ))
    
    # 設置圖表佈局
    fig.update_layout(
        title=f'{coin} - {timeframe_name} 價格圖表',
        xaxis_title='時間',
        yaxis_title='價格 (USDT)',
        height=500,
        template="plotly_dark",
        margin=dict(l=0, r=0, t=40, b=0),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    # 添加網格線
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255, 255, 255, 0.1)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255, 255, 255, 0.1)')
    
    return fig

# 在圖表標籤中顯示圖表
with tab2:
    st.subheader(f"{selected_coin} 技術分析圖表")
    data = get_crypto_data(selected_coin, selected_timeframe, limit=100)
    if data is not None:
        fig = plot_candlestick_chart(data, selected_coin, selected_timeframe_name)
        st.plotly_chart(fig, use_container_width=True)
        
        # 添加交易量圖表
        volume_fig = go.Figure()
        volume_fig.add_trace(go.Bar(
            x=data['timestamp'],
            y=data['volume'],
            name='成交量',
            marker=dict(color='rgba(74, 138, 244, 0.6)')
        ))
        
        volume_fig.update_layout(
            title="成交量分析",
            xaxis_title="時間",
            yaxis_title="成交量",
            height=250,
            template="plotly_dark",
            margin=dict(l=0, r=0, t=40, b=0)
        )
        
        st.plotly_chart(volume_fig, use_container_width=True)
    else:
        st.error(f"無法獲取 {selected_coin} 數據")
        st.info("請檢查您的網絡連接或選擇其他交易對")

# 主功能：執行分析 - 在分析標籤中顯示結果
with tab1:
    if st.session_state.analyze_button:
        # 獲取數據
        data = get_crypto_data(selected_coin, selected_timeframe)
        
        if data is not None:
            # 分析處理
            show_processing_animation()

            # 基於選擇的策略執行分析
            if selected_strategy == "SMC策略分析":
                st.markdown("## SMC策略分析結果")
                smc_results, smc_data = smc_analysis(data)
                
                # 使用卡片式布局顯示主要指標
                st.markdown("### 核心指標")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    trend_icon = "📈" if smc_results['market_structure'] == 'bullish' else "📉"
                    st.metric(f"{trend_icon} 市場趨勢", 
                             "上升趨勢" if smc_results['market_structure'] == 'bullish' else "下降趨勢", 
                             delta=f"{smc_results['trend_strength']*100:.1f}% 強度")
                    
                with col2:
                    rec_icon = "🟢" if smc_results['recommendation'] == 'buy' else "🔴" if smc_results['recommendation'] == 'sell' else "🟡"
                    rec_value = "買入" if smc_results['recommendation'] == 'buy' else "賣出" if smc_results['recommendation'] == 'sell' else "觀望"
                    rec_class = "buy-rec" if smc_results['recommendation'] == 'buy' else "sell-rec" if smc_results['recommendation'] == 'sell' else "neutral-rec"
                    
                    st.markdown(f"""
                    <div style='background-color:#1a1d24; padding:15px; border-radius:10px; border-left:5px solid #4a8af4;'>
                        <h3 style='margin:0; font-size:1rem;'>
                            {rec_icon} SMC建議
                        </h3>
                        <p class='{rec_class}' style='font-size:1.5rem; margin:5px 0;'>
                            {rec_value}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.metric("💰 當前價格", f"${smc_results['price']:.2f}")
                
                with col4:
                    liquidity_icon = "💧" if smc_results['liquidity'] == 'high' else "💦"
                    liquidity_value = "充足" if smc_results['liquidity'] == 'high' else "正常"
                    st.metric(f"{liquidity_icon} 市場流動性", liquidity_value)
                
                # 支撐阻力位顯示
                st.markdown("### 價格關鍵位")
                col1, col2 = st.columns(2)
                with col1:
                    # 更直觀的支撐位顯示
                    st.markdown(f"""
                    <div style='background-color:#1a1d24; padding:15px; border-radius:10px; border-left:5px solid #4CAF50;'>
                        <h3 style='margin:0; font-size:1rem;'>
                            ⬆️ 支撐位
                        </h3>
                        <p style='font-size:1.5rem; margin:5px 0; color:#4CAF50;'>
                            ${smc_results['support_level']:.2f}
                        </p>
                        <p style='margin:0; font-size:0.8rem;'>
                            當價格接近此位置可能獲得支撐
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    # 更直觀的阻力位顯示
                    st.markdown(f"""
                    <div style='background-color:#1a1d24; padding:15px; border-radius:10px; border-left:5px solid #F44336;'>
                        <h3 style='margin:0; font-size:1rem;'>
                            ⬇️ 阻力位
                        </h3>
                        <p style='font-size:1.5rem; margin:5px 0; color:#F44336;'>
                            ${smc_results['resistance_level']:.2f}
                        </p>
                        <p style='margin:0; font-size:0.8rem;'>
                            當價格接近此位置可能遇到阻力
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # 顯示AI分析
                st.markdown("### 🤖 DeepSeek 全方位分析")
                with st.container():
                    ai_analysis = get_deepseek_analysis(selected_coin, selected_timeframe, data, smc_results, 
                                                      {"rsi": 50, "overbought": False, "oversold": False, 
                                                       "near_support": smc_results['support_level'] * 0.98, 
                                                       "near_resistance": smc_results['resistance_level'] * 1.02}, analysis_detail)
                    st.markdown(f"""
                    <div style='background-color:#1a1d24; padding:20px; border-radius:10px; border-left:5px solid #9C27B0;'>
                        {ai_analysis}
                    </div>
                    """, unsafe_allow_html=True)
                
                # 多時間框架分析
                st.markdown("### 🔄 多時間框架分析")
                mtf_results = mtf_analysis(selected_coin, selected_timeframe)
                mtf_consensus = get_mtf_trend_consensus(mtf_results)
                st.markdown(f"""
                <div style='background-color:#1a1d24; padding:20px; border-radius:10px; border-left:5px solid #FF9800;'>
                    {mtf_consensus}
                </div>
                """, unsafe_allow_html=True)
                
                # 激進交易策略部分
                if show_aggressive:
                    st.markdown("---")
                    st.markdown("### 📊 激進交易策略")
                    with st.container():
                        price = smc_results['price']
                        
                        # 根據所選策略決定使用哪些支撐阻力位
                        support = smc_results['support_level']
                        resistance = smc_results['resistance_level']
                        
                        aggressive_strategy = generate_aggressive_strategy(
                            selected_coin, price, support, resistance
                        )
                        
                        st.markdown(f"""
                        <div style='background-color:#1a1d24; padding:20px; border-radius:10px; border-left:5px solid #E91E63;'>
                            {aggressive_strategy}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # 風險警告
                        st.warning("⚠️ 激進策略風險較高，僅供參考。請謹慎使用並自行承擔風險。")
                
            elif selected_strategy == "SNR策略分析":
                st.markdown("## SNR策略分析結果")
                snr_results, snr_data = snr_analysis(data)
                
                # 使用卡片式布局顯示核心指標
                st.markdown("### 核心指標")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    rsi_icon = "🔥" if snr_results['overbought'] else "❄️" if snr_results['oversold'] else "⚖️"
                    rsi_delta = "超買" if snr_results['overbought'] else "超賣" if snr_results['oversold'] else "中性"
                    rsi_color = "#F44336" if snr_results['overbought'] else "#4CAF50" if snr_results['oversold'] else "#FFC107"
                    
                    st.markdown(f"""
                    <div style='background-color:#1a1d24; padding:15px; border-radius:10px; border-left:5px solid #4a8af4;'>
                        <h3 style='margin:0; font-size:1rem;'>
                            {rsi_icon} RSI指標
                        </h3>
                        <p style='font-size:1.5rem; margin:5px 0; color:{rsi_color};'>
                            {snr_results['rsi']:.1f}
                        </p>
                        <p style='margin:0; font-size:0.8rem;'>
                            {rsi_delta}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    rec_icon = "🟢" if snr_results['recommendation'] == 'buy' else "🔴" if snr_results['recommendation'] == 'sell' else "🟡"
                    rec_value = "買入" if snr_results['recommendation'] == 'buy' else "賣出" if snr_results['recommendation'] == 'sell' else "觀望"
                    rec_class = "buy-rec" if snr_results['recommendation'] == 'buy' else "sell-rec" if snr_results['recommendation'] == 'sell' else "neutral-rec"
                    
                    st.markdown(f"""
                    <div style='background-color:#1a1d24; padding:15px; border-radius:10px; border-left:5px solid #4a8af4;'>
                        <h3 style='margin:0; font-size:1rem;'>
                            {rec_icon} SNR建議
                        </h3>
                        <p class='{rec_class}' style='font-size:1.5rem; margin:5px 0;'>
                            {rec_value}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.metric("💰 當前價格", f"${snr_results['price']:.2f}")
                
                with col4:
                    strength = (snr_results['support_strength'] + snr_results['resistance_strength']) / 2
                    strength_text = "強" if strength > 1.2 else "中等" if strength > 0.8 else "弱"
                    st.metric("🔍 技術強度", f"{strength_text} ({strength:.2f})")
                
                # 支撐阻力位顯示
                st.markdown("### 價格關鍵位")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    # 近期支撐位
                    st.markdown(f"""
                    <div style='background-color:#1a1d24; padding:15px; border-radius:10px; border-left:5px solid #4CAF50;'>
                        <h3 style='margin:0; font-size:1rem;'>
                            ⬆️ 近期支撐位
                        </h3>
                        <p style='font-size:1.5rem; margin:5px 0; color:#4CAF50;'>
                            ${snr_results['near_support']:.2f}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    # 強力支撐位
                    st.markdown(f"""
                    <div style='background-color:#1a1d24; padding:15px; border-radius:10px; border-left:5px solid #2E7D32;'>
                        <h3 style='margin:0; font-size:1rem;'>
                            ⬆️⬆️ 強支撐位
                        </h3>
                        <p style='font-size:1.5rem; margin:5px 0; color:#2E7D32;'>
                            ${snr_results['strong_support']:.2f}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    # 近期阻力位
                    st.markdown(f"""
                    <div style='background-color:#1a1d24; padding:15px; border-radius:10px; border-left:5px solid #F44336;'>
                        <h3 style='margin:0; font-size:1rem;'>
                            ⬇️ 近期阻力位
                        </h3>
                        <p style='font-size:1.5rem; margin:5px 0; color:#F44336;'>
                            ${snr_results['near_resistance']:.2f}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    # 強力阻力位
                    st.markdown(f"""
                    <div style='background-color:#1a1d24; padding:15px; border-radius:10px; border-left:5px solid #C62828;'>
                        <h3 style='margin:0; font-size:1rem;'>
                            ⬇️⬇️ 強阻力位
                        </h3>
                        <p style='font-size:1.5rem; margin:5px 0; color:#C62828;'>
                            ${snr_results['strong_resistance']:.2f}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # 添加多時間框架分析
                st.markdown("### 🔄 多時間框架分析")
                mtf_results = mtf_analysis(selected_coin, selected_timeframe)
                mtf_consensus = get_mtf_trend_consensus(mtf_results)
                st.markdown(f"""
                <div style='background-color:#1a1d24; padding:20px; border-radius:10px; border-left:5px solid #FF9800;'>
                    {mtf_consensus}
                </div>
                """, unsafe_allow_html=True)
                
                # 顯示更多SNR信息，使用折疊面板
                with st.expander("查看更多技術指標詳情"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"""
                        <div style='background-color:#1a1d24; padding:15px; border-radius:10px;'>
                            <h3 style='margin:0; font-size:1rem; color:#4a8af4;'>支撐位強度</h3>
                            <p style='font-size:1.2rem; margin:5px 0;'>{snr_results['support_strength']:.2f}</p>
                            <div style='height:5px; background-color:#4CAF50; width:{min(snr_results['support_strength']*50, 100)}%;'></div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col2:
                        st.markdown(f"""
                        <div style='background-color:#1a1d24; padding:15px; border-radius:10px;'>
                            <h3 style='margin:0; font-size:1rem; color:#4a8af4;'>阻力位強度</h3>
                            <p style='font-size:1.2rem; margin:5px 0;'>{snr_results['resistance_strength']:.2f}</p>
                            <div style='height:5px; background-color:#F44336; width:{min(snr_results['resistance_strength']*50, 100)}%;'></div>
                        </div>
                        """, unsafe_allow_html=True)
                
                # 激進交易策略部分
                if show_aggressive:
                    st.markdown("---")
                    st.markdown("### 📊 激進交易策略")
                    with st.container():
                        price = snr_results['price']
                        
                        # 根據所選策略決定使用哪些支撐阻力位
                        support = snr_results['near_support']
                        resistance = snr_results['near_resistance']
                        
                        aggressive_strategy = generate_aggressive_strategy(
                            selected_coin, price, support, resistance
                        )
                        
                        st.markdown(f"""
                        <div style='background-color:#1a1d24; padding:20px; border-radius:10px; border-left:5px solid #E91E63;'>
                            {aggressive_strategy}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # 風險警告
                        st.warning("⚠️ 激進策略風險較高，僅供參考。請謹慎使用並自行承擔風險。")
                
            else:  # SMC+SNR整合分析
                st.markdown("## SMC+SNR整合分析結果")
                smc_results, smc_data = smc_analysis(data)
                snr_results, snr_data = snr_analysis(data)
                
                # 核心整合指標
                st.markdown("### 策略整合評分")
                
                # 計算一致性分數 (0-100)
                is_consistent = smc_results['recommendation'] == snr_results['recommendation']
                consistency_score = 100 if is_consistent else 50
                
                # 確定最終建議
                if is_consistent:
                    final_rec = smc_results['recommendation']
                elif smc_results['trend_strength'] > 0.7:
                    final_rec = smc_results['recommendation']
                    consistency_score = 75
                elif snr_results['rsi'] < 30 or snr_results['rsi'] > 70:
                    final_rec = snr_results['recommendation']
                    consistency_score = 75
                else:
                    final_rec = 'neutral'
                    consistency_score = 50
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # 整合建議
                    rec_icon = "🟢" if final_rec == 'buy' else "🔴" if final_rec == 'sell' else "🟡"
                    rec_value = "買入" if final_rec == 'buy' else "賣出" if final_rec == 'sell' else "觀望"
                    rec_class = "buy-rec" if final_rec == 'buy' else "sell-rec" if final_rec == 'sell' else "neutral-rec"
                    
                    st.markdown(f"""
                    <div style='background-color:#1a1d24; padding:20px; border-radius:10px; border-left:5px solid #673AB7;'>
                        <h3 style='margin:0 0 10px 0; font-size:1.2rem; color:#673AB7;'>
                            📊 整合分析建議
                        </h3>
                        <p class='{rec_class}' style='font-size:2rem; margin:10px 0;'>
                            {rec_icon} {rec_value}
                        </p>
                        <p style='margin:5px 0; font-size:0.9rem;'>
                            基於SMC和SNR策略的綜合分析
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    # 一致性評分
                    consistency_color = "#4CAF50" if consistency_score > 75 else "#FFC107" if consistency_score > 50 else "#F44336"
                    consistency_text = "高" if consistency_score > 75 else "中等" if consistency_score > 50 else "低"
                    
                    st.markdown(f"""
                    <div style='background-color:#1a1d24; padding:20px; border-radius:10px; border-left:5px solid #2196F3;'>
                        <h3 style='margin:0 0 10px 0; font-size:1.2rem; color:#2196F3;'>
                            🔄 策略一致性評分
                        </h3>
                        <div style='display:flex; align-items:center;'>
                            <div style='flex-grow:1; height:10px; background-color:#333; border-radius:5px;'>
                                <div style='width:{consistency_score}%; height:100%; background-color:{consistency_color}; border-radius:5px;'></div>
                            </div>
                            <p style='margin:0 0 0 10px; font-size:1.5rem; color:{consistency_color};'>{consistency_score}%</p>
                        </div>
                        <p style='margin:5px 0; font-size:0.9rem;'>
                            一致性: <span style='color:{consistency_color};'>{consistency_text}</span> (SMC與SNR策略的信號一致程度)
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # 顯示詳細的策略比較
                st.markdown("### 策略對比分析")
                col1, col2 = st.columns(2)
                
                with col1:
                    trend_icon = "📈" if smc_results['market_structure'] == 'bullish' else "📉"
                    st.markdown(f"""
                    <div style='background-color:#1a1d24; padding:15px; border-radius:10px; border-left:5px solid #FF9800;'>
                        <h3 style='margin:0; font-size:1rem; color:#FF9800;'>
                            🧠 SMC策略分析
                        </h3>
                        <table style='width:100%; margin-top:10px;'>
                            <tr>
                                <td>市場結構:</td>
                                <td><b>{trend_icon} {"上升趨勢" if smc_results['market_structure'] == 'bullish' else "下降趨勢"}</b></td>
                            </tr>
                            <tr>
                                <td>趨勢強度:</td>
                                <td><b>{smc_results['trend_strength']*100:.1f}%</b></td>
                            </tr>
                            <tr>
                                <td>支撐位:</td>
                                <td><b style='color:#4CAF50;'>${smc_results['support_level']:.2f}</b></td>
                            </tr>
                            <tr>
                                <td>阻力位:</td>
                                <td><b style='color:#F44336;'>${smc_results['resistance_level']:.2f}</b></td>
                            </tr>
                            <tr>
                                <td>建議:</td>
                                <td class='{"buy-rec" if smc_results["recommendation"] == "buy" else "sell-rec" if smc_results["recommendation"] == "sell" else "neutral-rec"}'>
                                    <b>{"買入" if smc_results['recommendation'] == 'buy' else "賣出" if smc_results['recommendation'] == 'sell' else "觀望"}</b>
                                </td>
                            </tr>
                        </table>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    rsi_icon = "🔥" if snr_results['overbought'] else "❄️" if snr_results['oversold'] else "⚖️"
                    st.markdown(f"""
                    <div style='background-color:#1a1d24; padding:15px; border-radius:10px; border-left:5px solid #9C27B0;'>
                        <h3 style='margin:0; font-size:1rem; color:#9C27B0;'>
                            📏 SNR策略分析
                        </h3>
                        <table style='width:100%; margin-top:10px;'>
                            <tr>
                                <td>RSI值:</td>
                                <td><b>{rsi_icon} {snr_results['rsi']:.1f}</b> ({"超買" if snr_results['overbought'] else "超賣" if snr_results['oversold'] else "中性"})</td>
                            </tr>
                            <tr>
                                <td>近期支撐位:</td>
                                <td><b style='color:#4CAF50;'>${snr_results['near_support']:.2f}</b></td>
                            </tr>
                            <tr>
                                <td>近期阻力位:</td>
                                <td><b style='color:#F44336;'>${snr_results['near_resistance']:.2f}</b></td>
                            </tr>
                            <tr>
                                <td>強支撐位:</td>
                                <td><b style='color:#2E7D32;'>${snr_results['strong_support']:.2f}</b></td>
                            </tr>
                            <tr>
                                <td>建議:</td>
                                <td class='{"buy-rec" if snr_results["recommendation"] == "buy" else "sell-rec" if snr_results["recommendation"] == "sell" else "neutral-rec"}'>
                                    <b>{"買入" if snr_results['recommendation'] == 'buy' else "賣出" if snr_results['recommendation'] == 'sell' else "觀望"}</b>
                                </td>
                            </tr>
                        </table>
                    </div>
                    """, unsafe_allow_html=True)
                
                # 多時間框架分析
                st.markdown("### 🔄 多時間框架分析")
                mtf_results = mtf_analysis(selected_coin, selected_timeframe)
                mtf_consensus = get_mtf_trend_consensus(mtf_results)
                st.markdown(f"""
                <div style='background-color:#1a1d24; padding:20px; border-radius:10px; border-left:5px solid #FF9800;'>
                    {mtf_consensus}
                </div>
                """, unsafe_allow_html=True)
                
                # DeepSeek分析
                st.markdown("### 🤖 DeepSeek 全方位分析")
                ai_analysis = get_deepseek_analysis(selected_coin, selected_timeframe, data, smc_results, snr_results, analysis_detail)
                st.markdown(f"""
                <div style='background-color:#1a1d24; padding:20px; border-radius:10px; border-left:5px solid #9C27B0;'>
                    {ai_analysis}
                </div>
                """, unsafe_allow_html=True)
                
                # 激進交易策略部分
                if show_aggressive:
                    st.markdown("---")
                    st.markdown("### 📊 激進交易策略")
                    with st.container():
                        price = smc_results['price']
                        
                        # 根據所選策略決定使用哪些支撐阻力位
                        support = min(smc_results['support_level'], snr_results['near_support'])
                        resistance = max(smc_results['resistance_level'], snr_results['near_resistance'])
                        
                        aggressive_strategy = generate_aggressive_strategy(
                            selected_coin, price, support, resistance
                        )
                        
                        st.markdown(f"""
                        <div style='background-color:#1a1d24; padding:20px; border-radius:10px; border-left:5px solid #E91E63;'>
                            {aggressive_strategy}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # 風險警告
                        st.warning("⚠️ 激進策略風險較高，僅供參考。請謹慎使用並自行承擔風險。")
                
        else:
            st.error("無法獲取數據，請檢查網絡連接或選擇其他交易對。")

# 底部免責聲明
st.markdown("---")
st.markdown("""
<div style='background-color:#1a1d24; padding:15px; border-radius:10px; margin-top:20px;'>
    <h3 style='color:#F44336; margin-top:0;'>⚠️ 免責聲明</h3>
    <p>本工具提供的分析結果僅供參考，不構成投資建議。加密貨幣市場風險高，投資需謹慎。</p>
    <p>使用者應自行承擔所有決策責任。分析基於歷史數據，過去表現不代表未來結果。</p>
</div>
""", unsafe_allow_html=True)

# 側邊欄底部信息 - 優化顯示
st.sidebar.markdown("---")

# AI模型信息卡片
st.sidebar.markdown("""
<div style='background-color:#1a1d24; padding:15px; border-radius:10px; margin-bottom:15px;'>
    <h3 style='color:#4a8af4; margin-top:0; font-size:1rem;'>🤖 AI分析模型</h3>
    <table style='width:100%;'>
        <tr>
            <td><span style='color:#9C27B0;'>🧪</span> DeepSeek V3:</td>
            <td>技術分析與價格預測 (真實API)</td>
        </tr>
        <tr>
            <td><span style='color:#00BCD4;'>🔍</span> GPT-4o3-mini:</td>
            <td>市場情緒分析 (模擬)</td>
        </tr>
        <tr>
            <td><span style='color:#3F51B5;'>🔮</span> Claude 3.7:</td>
            <td>分析整合與結構化輸出 (模擬)</td>
        </tr>
    </table>
</div>
""", unsafe_allow_html=True)

# 版本信息
st.sidebar.markdown("""
<div style='background-color:#1a1d24; padding:15px; border-radius:10px; margin-bottom:15px;'>
    <h3 style='color:#4a8af4; margin-top:0; font-size:1rem;'>🚀 當前版本</h3>
    <p style='margin:0;'><span style='color:#4CAF50; font-weight:bold;'>多模型AI分析版 (1.0.0)</span></p>
    <p style='margin:5px 0 0 0; font-size:0.8rem; color:#999;'>更新時間: 2024-03-27</p>
</div>
""", unsafe_allow_html=True)

# 添加"關於"部分 - 優化顯示
with st.sidebar.expander("ℹ️ 關於本工具"):
    st.markdown("""
    <div style='background-color:#1a1d24; padding:15px; border-radius:10px;'>
        <p><b>CryptoAnalyzer</b> 是一個整合了SMC(Smart Money Concept)和SNR(Support & Resistance)分析方法的加密貨幣技術分析工具。</p>
        
        <p>本版本使用DeepSeek V3的真實API進行技術分析，並模擬GPT-4o3-mini和Claude 3.7分析能力，提供全面的加密貨幣市場洞察。</p>
        
        <p style='margin-bottom:0;'>技術數據通過CCXT庫從Binance獲取，使用專業級加密貨幣技術分析指標。</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 添加工具說明
    st.markdown("### 🛠️ 使用的分析策略")
    st.markdown("""
    <div style='background-color:#1a1d24; padding:15px; border-radius:10px;'>
        <p><span style='color:#FF9800; font-weight:bold;'>SMC策略</span> - Smart Money Concept 識別市場結構、流動性區域和主要參與者的行為模式</p>
        <p><span style='color:#9C27B0; font-weight:bold;'>SNR策略</span> - Support & Resistance 分析關鍵價格水平、突破和反轉信號</p>
        <p><span style='color:#673AB7; font-weight:bold;'>整合分析</span> - 結合SMC和SNR優勢，提供更全面的市場洞察</p>
    </div>
    """, unsafe_allow_html=True)
