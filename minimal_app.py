import streamlit as st

# Streamlit頁面設定 - 必須是第一個 Streamlit 命令
st.set_page_config(
    page_title="CryptoAnalyzer - 加密貨幣分析工具",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="📊"
)

# 顯示載入狀態
st.markdown("""
<div style="text-align: center; padding:20px;">
    <h1>CryptoAnalyzer - 加密貨幣分析工具</h1>
    <p>正在載入應用程式...</p>
</div>
""", unsafe_allow_html=True)

# 導入必要的模組
import sys
import os
import pandas as pd
import numpy as np
import time
import random
from datetime import datetime
import plotly.graph_objects as go
import requests
import json
from openai import OpenAI
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

try:
    # 直接導入 main 函數而不是整個模組
    from crypto_analyzer_fixed import main
    
    # 隱藏載入訊息
    st.empty()
    
    # 執行主函數
    main()
    
except Exception as e:
    st.error(f"載入應用程式時發生錯誤: {str(e)}")
    st.exception(e)
    
    # 顯示錯誤詳情
    error_type = type(e).__name__
    error_message = str(e)
    
    st.markdown(f"""
    ### 發生錯誤: {error_type}
    
    錯誤訊息: {error_message}
    
    ### 請嘗試以下解決方法:
    1. 刷新頁面
    2. 使用不同的瀏覽器
    3. 清除瀏覽器緩存
    """) 