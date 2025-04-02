import streamlit as st

# Streamlit頁面設定 - 必須是第一個 Streamlit 命令
st.set_page_config(
    page_title="CryptoAnalyzer - 加密貨幣分析工具",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="📊"
)

# 顯示 Loading 頁面
st.markdown("""
<div style='text-align: center'>
    <h1>🚀 CryptoAnalyzer 正在加載中...</h1>
    <p>請稍候，正在初始化分析環境...</p>
</div>
""", unsafe_allow_html=True)

# 導入主程式
try:
    # 導入主程式
    from crypto_analyzer_fixed import run_app
    
    # 運行主應用
    run_app()
    
except Exception as e:
    st.error(f"應用加載失敗: {str(e)}")
    st.error("詳細錯誤信息:")
    st.exception(e)
    
    st.markdown("""
    ### 嘗試以下解決方法:
    1. 刷新頁面
    2. 清除瀏覽器緩存
    3. 使用 Chrome 或 Firefox 瀏覽器
    4. 檢查網絡連接
    """) 