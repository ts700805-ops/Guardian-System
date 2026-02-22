import streamlit as st
import json
import os

# 設定網頁標題與圖示
st.set_page_config(page_title="異常守護者 2.0 Web", page_icon="🛡️")

st.title("🛡️ 異常守護者：維修方案查詢系統")

# 讀取 handbook.json
def load_data():
    if os.path.exists('handbook.json'):
        with open('handbook.json', 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    return []

data = load_data()

# 搜尋框
query = st.text_input("🔍 請輸入關鍵字（例如：馬達、感測器）", "")

if query:
    # 搜尋邏輯
    results = [item for item in data if query.lower() in (item.get('issue', '') + item.get('keyword', '')).lower()]
    
    if results:
        for item in results:
            with st.expander(f"📌 問題：{item['issue']}", expanded=True):
                st.write("**【排除建議方案】**")
                # 處理分號換行
                steps = item.get('solution', '').replace('；', ';').split(';')
                for i, step in enumerate(steps, 1):
                    if step.strip():
                        st.write(f"{i}. {step.strip()}")
    else:
        st.error("❌ 找不到相關方案，請嘗試其他關鍵字。")
else:
    st.info("💡 請在上方輸入關鍵字開始查詢")
