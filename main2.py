import streamlit as st

def render_page():
    st.markdown("""
        <div class="main-header">
            <h2>📈 品質異常紀錄中心</h2>
            <p style="margin:0; opacity:0.8;">這是透過 main2.py 載入的品質異常紀錄查詢頁面測試。</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.info("💡 目前為測試模組，您可以隨時在此擴充品質異常紀錄相關的查詢、統計或新增功能！")
    
    # 簡單的測試互動介面
    q_input = st.text_input("🔍 輸入品質異常關鍵字進行查詢測試")
    if st.button("查詢品質異常紀錄"):
        if q_input:
            st.success(f"成功查詢到與「{q_input}」相關的品質異常紀錄測試資料！")
        else:
            st.warning("請輸入查詢關鍵字。")