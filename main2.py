import streamlit as st

def render_page():
    # 注入專屬於品質異常中心的深紅色戰情室風格 CSS
    st.markdown("""
        <style>
        /* 品質異常中心專屬深紅調漸層背景 */
        .stApp {
            background: linear-gradient(180deg, #1a0909 0%, #240d0d 50%, #3d1414 100%) !important;
            background-attachment: fixed;
            color: #fce8e8 !important;
        }
        .quality-header {
            background: linear-gradient(135deg, #5c1d1d, #381111);
            color: #ffffff;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.5);
            border: 1px solid #8a2be2;
        }
        .quality-card {
            background-color: #2b1111;
            border-left: 6px solid #e63946;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.4);
            border: 1px solid #5c1d1d;
        }
        h1, h2, h3, h4, h5, h6, label, .stMarkdown p {
            color: #fce8e8 !important;
        }
        /* 紅色風格下的輸入框與按鈕優化 */
        input, textarea, select {
            background-color: #2b1111 !important;
            color: #fce8e8 !important;
            border: 1px solid #8a2be2 !important;
        }
        .stTextInput input, .stTextArea textarea {
            background-color: #2b1111 !important;
            color: #fce8e8 !important;
        }
        .stButton>button {
            background-color: #5c1d1d !important;
            color: #ffffff !important;
            border: 1px solid #e63946 !important;
            font-weight: bold;
        }
        .stButton>button:hover {
            background-color: #8a2be2 !important;
            color: #ffffff !important;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div class="quality-header">
            <h2>📈 品質異常紀錄中心</h2>
            <p style="margin:0; opacity:0.8;">此頁面已切換為獨立的深紅色專屬戰情室風格。</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="quality-card">', unsafe_allow_html=True)
    st.info("💡 您可以在此擴充品質異常紀錄查詢、品質缺失統計與分析圖表！")
    
    q_input = st.text_input("🔍 輸入品質異常關鍵字進行檢索")
    if st.button("查詢品質異常紀錄"):
        if q_input:
            st.success(f"成功查詢到與「{q_input}」相關的品質異常紀錄！")
        else:
            st.warning("請輸入查詢關鍵字。")
    st.markdown('</div>', unsafe_allow_html=True)
