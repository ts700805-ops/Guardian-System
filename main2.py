import streamlit as st
import datetime
from firebase_admin import db

def render_page(current_menu):
    # 注入淡橙色背景與深藍色字體的優化 CSS
    st.markdown("""
        <style>
        .stApp {
            background: linear-gradient(180deg, #fceade 0%, #f7d6bd 50%, #f2c29e 100%) !important;
            background-attachment: fixed;
        }
        .quality-header {
            background: linear-gradient(135deg, #e07a5f, #d46342);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.15);
            border: 1px solid #f4a261;
        }
        .quality-header h2 {
            color: #0b192c !important;
        }
        .quality-card {
            background-color: #faedcd;
            border-left: 6px solid #e07a5f;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border: 1px solid #d4a373;
        }
        h1, h2, h3, h4, h5, h6, 
        label, 
        .stMarkdown p, 
        span, 
        div[data-testid="stMarkdownContainer"] p,
        .stTextInput label, 
        .stDateInput label, 
        .stSelectbox label,
        .stTextArea label {
            color: #0b192c !important;
        }
        input, textarea, select {
            background-color: #ffffff !important;
            color: #0b192c !important;
            border: 1px solid #e07a5f !important;
        }
        .stTextInput input, .stTextArea textarea {
            background-color: #ffffff !important;
            color: #0b192c !important;
        }
        section[data-testid="stSidebar"] .stButton>button,
        .stButton>button {
            width: 100%;
            background-color: #e07a5f !important;
            border: 1px solid #bc4749 !important;
            border-radius: 8px;
            font-weight: bold;
        }
        section[data-testid="stSidebar"] .stButton>button p,
        section[data-testid="stSidebar"] .stButton>button span,
        .stButton>button p,
        .stButton>button span {
            color: #0b192c !important;
        }
        section[data-testid="stSidebar"] .stButton>button:hover,
        .stButton>button:hover {
            background-color: #f4a261 !important;
            border: 1px solid #e07a5f !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # 讀取與儲存分類選項
    def load_categories():
        ref = db.reference('quality_categories')
        cats = ref.get()
        if not cats:
            cats = ["設備異常", "材料異常", "操作疏失", "環境因素", "其他"]
            ref.set(cats)
        return cats

    # 讀取與儲存品質異常紀錄
    def load_quality_records():
        ref = db.reference('quality_records')
        data = ref.get()
        return data if data else []

    def save_quality_records(records):
        db.reference('quality_records').set(records)

    categories = load_categories()

    if current_menu == "📈 異常紀錄查詢":
        st.markdown("""
            <div class="quality-header">
                <h2>📈 品質異常紀錄查詢與模糊搜尋</h2>
            </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="quality-card">', unsafe_allow_html=True)
        query = st.text_input("🔍 輸入關鍵字進行全欄位模糊搜尋 (可針對製令、分類、內容、排除方式、對策、狀況、人員等)")
        
        records = load_quality_records()
        
        if query.strip():
            search_terms = query.lower().split()
            filtered_records = []
            for rec in records:
                combined_text = f"{rec.get('order', '')} {rec.get('date', '')} {rec.get('category', '')} {rec.get('content', '')} {rec.get('solution', '')} {rec.get('countermeasure', '')} {rec.get('status', '')} {rec.get('person', '')}".lower()
                if all(term in combined_text for term in search_terms):
                    filtered_records.append(rec)
        else:
            filtered_records = records

        st.markdown(f"### 📋 搜尋結果 (共 {len(filtered_records)} 筆)")
        
        if filtered_records:
            for i, rec in enumerate(filtered_records):
                with st.expander(f"📌 製令：{rec.get('order', '無')} | 日期：{rec.get('date', '')} | 分類：{rec.get('category', '')} | 人員：{rec.get('person', '')}"):
                    st.markdown(f"**1. 製令：** {rec.get('order', '')}")
                    st.markdown(f"**2. 建立日期：** {rec.get('date', '')}")
                    st.markdown(f"**3. 異常分類：** {rec.get('category', '')}")
                    st.markdown(f"**4. 異常內容：** {rec.get('content', '')}")
                    st.markdown(f"**5. 排除方式：** {rec.get('solution', '')}")
                    st.markdown(f"**6. 對策：** {rec.get('countermeasure', '')}")
                    st.markdown(f"**7. 追蹤狀況：** {rec.get('status', '')}")
                    st.markdown(f"**8. 異常人員：** {rec.get('person', '')}")
        else:
            st.info("尚無符合條件的品質異常紀錄。")
            
        st.markdown('</div>', unsafe_allow_html=True)

    elif current_menu == "➕ 異常項目建立":
        st.markdown("""
            <div class="quality-header">
                <h2>➕ 06. 異常項目建立</h2>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("""
            <div class="quality-card">
                <p style="margin:0; font-weight:bold;">請填寫以下品質異常相關資料（內容可留空直接建立）。</p>
            </div>
        """, unsafe_allow_html=True)

        with st.form("quality_create_form"):
            col1, col2 = st.columns(2)
            with col1:
                f_order = st.text_input("1. 製令")
                f_date = st.date_input("2. 建立日期", value=datetime.date.today())
                f_category = st.selectbox("3. 異常分類", options=categories)
                f_content = st.text_area("4. 異常內容")
            with col2:
                f_solution = st.text_area("5. 排除方式")
                f_countermeasure = st.text_area("6. 對策")
                f_status = st.text_input("7. 追蹤狀況")
                f_person = st.text_input("8. 異常人員")

            submitted = st.form_submit_button("🚀 確認建立異常項目", use_container_width=True)
            if submitted:
                new_record = {
                    "order": f_order,
                    "date": str(f_date),
                    "category": f_category,
                    "content": f_content,
                    "solution": f_solution,
                    "countermeasure": f_countermeasure,
                    "status": f_status,
                    "person": f_person
                }
                
                records = load_quality_records()
                records.insert(0, new_record)
                save_quality_records(records)
                
                st.balloons()
                st.success("🎉 異常項目建立成功並已儲存至資料庫！")

    elif current_menu == "07. 異常後台管理":
        st.markdown("""
            <div class="quality-header">
                <h2>07. ⚙️ 異常後台管理 (分類設定)</h2>
            </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="quality-card">', unsafe_allow_html=True)
        st.markdown("### 📋 設定異常分類選項")
        st.markdown("請在下方文字框中輸入分類項目，多個選項請用半形或全形逗號 `,` 分隔（例如：`設備異常, 材料異常, 操作疏失`）。")

        current_str = ", ".join(categories)
        
        with st.form("category_edit_form"):
            cats_input = st.text_area("分類項目清單 (以逗號分隔)", value=current_str, height=150)
            submitted_cats = st.form_submit_button("💾 儲存分類設定", use_container_width=True)
            
            if submitted_cats:
                raw_list = cats_input.replace('，', ',').split(',')
                new_cats = [item.strip() for item in raw_list if item.strip()]
                
                if new_cats:
                    db.reference('quality_categories').set(new_cats)
                    st.balloons()
                    st.success("🎉 下拉式選單分類設定已成功更新！")
                else:
                    st.warning("⚠️ 請至少輸入一個有效的分類項目。")
        st.markdown('</div>', unsafe_allow_html=True)
