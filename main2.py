import streamlit as st
import datetime

def render_page(current_menu):
    # 注入專屬於品質異常中心的橙色戰情室風格 CSS
    st.markdown("""
        <style>
        .stApp {
            background: linear-gradient(180deg, #1f1309 0%, #2e1d0d 50%, #4d3114 100%) !important;
            background-attachment: fixed;
            color: #faedcd !important;
        }
        .quality-header {
            background: linear-gradient(135deg, #b05c1e, #803e11);
            color: #ffffff;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.5);
            border: 1px solid #d4a373;
        }
        .quality-card {
            background-color: #2b1c11;
            border-left: 6px solid #f4a261;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.4);
            border: 1px solid #803e11;
        }
        h1, h2, h3, h4, h5, h6, label, .stMarkdown p {
            color: #faedcd !important;
        }
        input, textarea, select {
            background-color: #2b1c11 !important;
            color: #faedcd !important;
            border: 1px solid #d4a373 !important;
        }
        .stTextInput input, .stTextArea textarea {
            background-color: #2b1c11 !important;
            color: #faedcd !important;
        }
        /* 品質異常側邊欄按鈕設計 (橙色系) */
        section[data-testid="stSidebar"] .stButton>button {
            width: 100%;
            background-color: #2b1c11 !important;
            color: #ffffff !important;
            border: 1px solid #803e11 !important;
            border-radius: 8px;
            text-align: left;
            font-weight: bold;
            margin-bottom: 4px;
        }
        section[data-testid="stSidebar"] .stButton>button:hover {
            background-color: #b05c1e !important;
            border: 1px solid #f4a261 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    if current_menu == "📈 異常紀錄查詢":
        st.markdown("""
            <div class="quality-header">
                <h2>📈 品質異常紀錄中心</h2>
            </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="quality-card">', unsafe_allow_html=True)
        q_input = st.text_input("🔍 輸入品質異常關鍵字進行檢索")
        if st.button("查詢品質異常紀錄", key="ql_search"):
            if q_input:
                st.success(f"成功查詢到與「{q_input}」相關的品質異常紀錄！")
            else:
                st.warning("請輸入查詢關鍵字。")
        st.markdown('</div>', unsafe_allow_html=True)

    elif current_menu == "➕ 異常項目建立":
        st.markdown("""
            <div class="quality-header">
                <h2>➕ 06. 異常項目建立</h2>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("""
            <div class="quality-card">
                <p style="opacity:0.8; margin:0;">請填寫以下品質異常相關資料（內容可留空直接建立）。</p>
            </div>
        """, unsafe_allow_html=True)

        with st.form("quality_create_form"):
            col1, col2 = st.columns(2)
            with col1:
                f_order = st.text_input("1. 製令")
                f_date = st.date_input("2. 建立日期", value=datetime.date.today())
                f_category = st.text_input("3. 異常分類")
                f_content = st.text_area("4. 異常內容")
            with col2:
                f_solution = st.text_area("5. 排除方式")
                f_countermeasure = st.text_area("6. 對策")
                f_status = st.text_input("7. 追蹤狀況")
                f_person = st.text_input("8. 異常人員")

            submitted = st.form_submit_button("🚀 確認建立異常項目", use_container_width=True)
            if submitted:
                st.balloons()
                st.success("🎉 異常項目建立成功！（資料已暫存）")
