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

    # 讀取 Firebase 上的異常分類清單 (若無則給予預設值)
    def load_categories():
        ref = db.reference('quality_categories')
        cats = ref.get()
        if not cats:
            cats = ["設備異常", "材料異常", "操作疏失", "環境因素", "其他"]
            ref.set(cats)
        return cats

    def save_categories(cats):
        db.reference('quality_categories').set(cats)

    categories = load_categories()

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
                <p style="margin:0; font-weight:bold;">請填寫以下品質異常相關資料（內容可留空直接建立）。</p>
            </div>
        """, unsafe_allow_html=True)

        with st.form("quality_create_form"):
            col1, col2 = st.columns(2)
            with col1:
                f_order = st.text_input("1. 製令")
                f_date = st.date_input("2. 建立日期", value=datetime.date.today())
                # 3. 異常分類改為動態下拉式選單
                f_category = st.selectbox("3. 異常分類", options=categories)
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

    elif current_menu == "07. 異常後台管理":
        st.markdown("""
            <div class="quality-header">
                <h2>07. ⚙️ 異常後台管理 (分類設定)</h2>
            </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="quality-card">', unsafe_allow_html=True)
        st.markdown("### 📋 目前的異常分類選項")
        
        # 顯示與編輯現有分類
        for idx, cat in enumerate(categories):
            col_c1, col_c2 = st.columns([4, 1])
            with col_c1:
                updated_cat = st.text_input(f"分類 {idx+1}", value=cat, key=f"cat_input_{idx}")
                categories[idx] = updated_cat
            with col_c2:
                if st.button("🗑️ 刪除", key=f"del_cat_{idx}"):
                    categories.pop(idx)
                    save_categories(categories)
                    st.success("已刪除分類！")
                    st.rerun()

        st.markdown("---")
        st.markdown("### ➕ 新增分類選項")
        new_cat = st.text_input("新異常分類名稱", key="new_cat_name")
        if st.button("確認新增分類", key="add_cat_btn"):
            if new_cat.strip() and new_cat.strip() not in categories:
                categories.append(new_cat.strip())
                save_categories(categories)
                st.success(f"成功新增分類：{new_cat}")
                st.rerun()
            else:
                st.warning("請輸入有效的分類名稱或避免重複。")

        if st.button("儲存所有分類變更", key="save_cats_btn"):
            save_categories([c.strip() for c in categories if c.strip()])
            st.balloons()
            st.success("🎉 分類設定已成功同步更新！")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
