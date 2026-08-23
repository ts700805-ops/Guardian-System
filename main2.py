import streamlit as st
import datetime

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
        </div>
    """, unsafe_allow_html=True)

    # 側邊欄或頁面內的子導航
    sub_menu = st.sidebar.radio("品質異常選單", ["🔍 異常紀錄查詢", "➕ 06. 異常項目建立"], key="quality_sub_menu")

    if sub_menu == "🔍 異常紀錄查詢":
        st.markdown('<div class="quality-card">', unsafe_allow_html=True)
        q_input = st.text_input("🔍 輸入品質異常關鍵字進行檢索")
        if st.button("查詢品質異常紀錄"):
            if q_input:
                st.success(f"成功查詢到與「{q_input}」相關的品質異常紀錄！")
            else:
                st.warning("請輸入查詢關鍵字。")
        st.markdown('</div>', unsafe_allow_html=True)

    elif sub_menu == "➕ 06. 異常項目建立":
        st.markdown("""
            <div class="quality-card">
                <h3>➕ 06. 異常項目建立</h3>
                <p style="opacity:0.8;">請填寫以下品質異常相關資料（內容可留空直接建立）。</p>
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
