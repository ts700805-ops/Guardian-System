import streamlit as st
import datetime
import pandas as pd
import altair as alt
from firebase_admin import db

def render_page(current_menu):
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

    def load_categories():
        ref = db.reference('quality_categories')
        cats = ref.get()
        if not cats:
            cats = ["設備異常", "材料異常", "操作疏失", "環境因素", "其他"]
            ref.set(cats)
        return cats

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
                <h2>📈 品質異常紀錄查詢與管理</h2>
            </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="quality-card">', unsafe_allow_html=True)
        query = st.text_input("🔍 輸入關鍵字進行全欄位模糊搜尋 (製令、分類、內容、排除方式、對策、狀況、人員等)")
        
        records = load_quality_records()
        
        if query.strip():
            search_terms = query.lower().split()
            filtered_indices = []
            for idx, rec in enumerate(records):
                combined_text = f"{rec.get('order', '')} {rec.get('date', '')} {rec.get('category', '')} {rec.get('content', '')} {rec.get('solution', '')} {rec.get('countermeasure', '')} {rec.get('status', '')} {rec.get('person', '')}".lower()
                if all(term in combined_text for term in search_terms):
                    filtered_indices.append(idx)
        else:
            filtered_indices = list(range(len(records)))

        st.markdown(f"### 📋 搜尋結果總覽 (共 {len(filtered_indices)} 筆)")
        
        if filtered_indices:
            for idx in filtered_indices:
                rec = records[idx]
                card_label = f"📌 【製令：{rec.get('order', '無')}】 日期：{rec.get('date', '')} | 分類：{rec.get('category', '')} | 人員：{rec.get('person', '')}"
                
                with st.expander(card_label):
                    tab_view, tab_edit, tab_del = st.tabs(["👁️ 內容檢視", "✏️ 編輯修改", "🗑️ 刪除紀錄"])
                    
                    with tab_view:
                        col_v1, col_v2 = st.columns(2)
                        with col_v1:
                            st.markdown(f"**1. 製令：** {rec.get('order', '')}")
                            st.markdown(f"**2. 建立日期：** {rec.get('date', '')}")
                            st.markdown(f"**3. 異常分類：** {rec.get('category', '')}")
                            st.markdown(f"**4. 異常內容：** {rec.get('content', '')}")
                        with col_v2:
                            st.markdown(f"**5. 排除方式：** {rec.get('solution', '')}")
                            st.markdown(f"**6. 對策：** {rec.get('countermeasure', '')}")
                            st.markdown(f"**7. 追蹤狀況：** {rec.get('status', '')}")
                            st.markdown(f"**8. 異常人員：** {rec.get('person', '')}")

                    with tab_edit:
                        with st.form(f"edit_form_{idx}"):
                            e_order = st.text_input("1. 製令", value=rec.get('order', ''), key=f"e_ord_{idx}")
                            try:
                                default_date = datetime.datetime.strptime(rec.get('date', str(datetime.date.today())), "%Y-%m-%d").date()
                            except:
                                default_date = datetime.date.today()
                            e_date = st.date_input("2. 建立日期", value=default_date, key=f"e_date_{idx}")
                            
                            cat_list = categories
                            curr_cat = rec.get('category', '')
                            cat_index = cat_list.index(curr_cat) if curr_cat in cat_list else 0
                            e_category = st.selectbox("3. 異常分類", options=cat_list, index=cat_index, key=f"e_cat_{idx}")
                            
                            e_content = st.text_area("4. 異常內容", value=rec.get('content', ''), key=f"e_cont_{idx}")
                            e_solution = st.text_area("5. 排除方式", value=rec.get('solution', ''), key=f"e_sol_{idx}")
                            e_countermeasure = st.text_area("6. 對策", value=rec.get('countermeasure', ''), key=f"e_cm_{idx}")
                            e_status = st.text_input("7. 追蹤狀況", value=rec.get('status', ''), key=f"e_stat_{idx}")
                            e_person = st.text_input("8. 異常人員", value=rec.get('person', ''), key=f"e_pers_{idx}")
                            
                            e_pwd = st.text_input("請輸入授權密碼", type="password", key=f"e_pwd_{idx}")
                            
                            submitted_edit = st.form_submit_button("💾 確認儲存修改", use_container_width=True)
                            if submitted_edit:
                                if e_pwd == "0000":
                                    records[idx] = {
                                        "order": e_order,
                                        "date": str(e_date),
                                        "category": e_category,
                                        "content": e_content,
                                        "solution": e_solution,
                                        "countermeasure": e_countermeasure,
                                        "status": e_status,
                                        "person": e_person
                                    }
                                    save_quality_records(records)
                                    st.balloons()
                                    st.success("🎉 紀錄修改成功！")
                                    st.rerun()
                                else:
                                    st.error("❌ 授權密碼錯誤！")

                    with tab_del:
                        with st.form(f"delete_form_{idx}"):
                            st.warning("⚠️ 刪除後將無法復原，請謹慎操作。")
                            d_pwd = st.text_input("請輸入授權密碼", type="password", key=f"d_pwd_{idx}")
                            submitted_del = st.form_submit_button("🚨 確認刪除此筆紀錄", use_container_width=True)
                            if submitted_del:
                                if d_pwd == "0000":
                                    records.pop(idx)
                                    save_quality_records(records)
                                    st.balloons()
                                    st.success("🗑️ 紀錄已成功刪除！")
                                    st.rerun()
                                else:
                                    st.error("❌ 授權密碼錯誤！")
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

    elif current_menu == "08. 品質異常分析":
        st.markdown("""
            <div class="quality-header">
                <h2>📊 08. 品質異常分析報表</h2>
            </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="quality-card">', unsafe_allow_html=True)
        st.markdown("### 📅 選擇分析日期區間")
        
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            start_date = st.date_input("開始日期", value=datetime.date.today() - datetime.timedelta(days=30))
        with col_d2:
            end_date = st.date_input("結束日期", value=datetime.date.today())

        records = load_quality_records()

        filtered_recs = []
        for rec in records:
            rec_date_str = rec.get('date', '')
            try:
                rec_date = datetime.datetime.strptime(rec_date_str, "%Y-%m-%d").date()
                if start_date <= rec_date <= end_date:
                    filtered_recs.append(rec)
            except:
                pass

        if filtered_recs:
            df = pd.DataFrame(filtered_recs)
            
            st.markdown("---")
            st.markdown("### 2. 異常分類百分比 (彩色圓餅圖)")
            
            total_cnt = len(filtered_recs)
            cat_counts = df['category'].value_counts()
            
            chart_data = []
            for cat, cnt in cat_counts.items():
                pct = round((cnt / total_cnt) * 100, 1)
                chart_data.append({
                    '分類': cat,
                    '件數': cnt,
                    '百分比': pct,
                    '標籤文字': f"{cat} ({pct}%)"
                })
            chart_df = pd.DataFrame(chart_data)

            # 使用多彩配色盤 (category10) 讓圓餅圖呈現豐富色彩
            base = alt.Chart(chart_df).encode(
                theta=alt.Theta(field="件數", type="quantitative"),
                color=alt.Color(field="分類", type="nominal", scale=alt.Scale(scheme="category10"), legend=alt.Legend(title="異常分類"))
            )

            pie = base.mark_arc(innerRadius=60, outerRadius=120)
            
            # 將分類與百分比放大顯示在外圍
            text = base.mark_text(radius=150, size=15, fontWeight="bold").encode(
                text=alt.Text(field="標籤文字", type="nominal")
            )

            st.altair_chart((pie + text).properties(width=700, height=500), use_container_width=True)

            ratio_data = []
            for cat, cnt in cat_counts.items():
                pct = round((cnt / total_cnt) * 100, 1)
                ratio_data.append({"異常分類": cat, "件數": cnt, "佔比百分比": f"{pct}%"})
            st.table(pd.DataFrame(ratio_data))

            st.markdown("---")
            st.markdown("### 1. 明細 (符合條件的詳細異常紀錄)")
            st.dataframe(df[['order', 'date', 'category', 'content', 'solution', 'countermeasure', 'status', 'person']], use_container_width=True)
            
        else:
            st.info("ℹ️ 於所選的日期區間內尚無品質異常紀錄資料。")
            
        st.markdown('</div>', unsafe_allow_html=True)
