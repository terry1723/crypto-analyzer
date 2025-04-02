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

# 導入主程式模組
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
    # 顯示應用程式
    import crypto_analyzer_fixed
    st.success("成功載入應用程式！")
    # 隱藏成功訊息
    st.empty()
    
except Exception as e:
    st.error(f"載入應用程式時發生錯誤: {str(e)}")
    st.exception(e)
    
    st.markdown("""
    ### 請嘗試以下解決方法:
    1. 刷新頁面
    2. 使用不同的瀏覽器
    3. 清除瀏覽器緩存
    """) 