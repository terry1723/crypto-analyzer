import streamlit as st

# 最基本的頁面設定
st.set_page_config(
    page_title="簡易測試",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 顯示最簡單的頁面內容
st.title("診斷測試頁面")
st.write("如果您能看到此頁面，表示 Streamlit 基本功能運作正常。")

# 側邊欄
st.sidebar.title("測試選項")
option = st.sidebar.selectbox("選擇測試項目", ["選項1", "選項2", "選項3"])

# 主頁面內容
st.write(f"您選擇了: {option}")

# 添加一個簡單的按鈕
if st.button("點擊測試"):
    st.success("按鈕點擊成功！")

# 顯示一些基本資訊
st.info("這是一個診斷應用，用於測試 Streamlit Cloud 部署是否正常運作。") 