import streamlit as st
import json
import os
import datetime
import re
import pandas as pd
from collections import Counter
import firebase_admin
from firebase_admin import credentials, db

# --- 基礎設定 ---
VERSION_SN = "v2026.08.22-29"  # 程式版本流水號自動 +1
st.set_page_config(page_title=f"異常守護者系統 ({VERSION_SN})", page_icon="🛡️", layout="wide")

# --- 自定義專業深色綠調戰情室風格排版與高對比深淺色優化 ---
st.markdown("""
    <style>
    /* 整個頁面主體套用深色戰情室風格，底部漸層綠色 */
    .stApp {
        background: linear-gradient(180deg, #091310 0%, #0d1f18 50%, #14362b 100%);
        background-attachment: fixed;
        color: #f1f8f6;
    }
    /* 全面套用至側邊欄導航介面 */
    section[data-testid="stSidebar"] {
        background-color: #0b1a14 !important;
        border-right: 1px solid #1b4d3e;
    }
    section[data-testid="stSidebar"] * {
        color: #f1f8f6 !important;
    }
    .main-header {
        background: linear-gradient(135deg, #1b4d3e, #0f2d22);
        color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.4);
        border: 1px solid #2d6a4f;
    }
    .query-card {
        background-color: #112a21;
        border-left: 6px solid #52b788;
        padding: 20px;
        border-radius: 8px;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        border: 1px solid #1b4d3e;
    }
    .solution-box {
        background-color: #143026;
        padding: 15px;
        border-radius: 6px;
        margin-top: 10px;
        margin-bottom: 15px;
        border: 1px solid #2d6a4f;
    }
    /* 優化文字與標題的高對比度 */
    h1, h2, h3, h4, h5, h6, label, .stMarkdown p {
        color: #f1f8f6 !important;
    }
    /* 統計頁面標題與表格內容黃色專用與加上線格 */
    .stat-title {
        color: #ffd700 !important;
    }
    div[data-testid="stTable"] table, 
    div[data-testid="stTable"] table th, 
    div[data-testid="stTable"] table td {
        color: #ffd700 !important;
        border: 1px solid #2d6a4f !important;
        border-collapse: collapse !important;
    }
    div[data-testid="stTable"] span {
        color: #ffd700 !important;
    }
    /* 修正輸入框背景與文字顏色，解決過亮看不清楚的問題 */
    input, textarea, select {
        background-color: #112a21 !important;
        color: #f1f8f6 !important;
        border: 1px solid #2d6a4f !important;
    }
    .stTextInput input, .stTextArea textarea {
        background-color: #112a21 !important;
        color: #f1f8f6 !important;
    }
    /* 按鈕深淺色搭配優化 */
    .stButton>button {
        background-color: #1b4d3e !important;
        color: #ffffff !important;
        border: 1px solid #52b788 !important;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #2d6a4f !important;
        color: #ffffff !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- Firebase 初始化 ---
if not firebase_admin._apps:
    try:
        fb_creds = json.loads(st.secrets["firebase"]["service_account"])
        fb_url = st.secrets["firebase"]["databaseURL"]
        cred = credentials.Certificate(fb_creds)
        firebase_admin.initialize_app(cred, {'databaseURL': fb_url})
    except Exception as e:
        st.error(f"Firebase 初始化失敗：{e}")

# 獲取台灣時間 (UTC+8)
def get_taiwan_time():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))

# 檔案路徑 (僅用於首次遷移資料)
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
USER_FILE = os.path.join(BASE_PATH, 'users.json')
HANDBOOK_FILE = os.path.join(BASE_PATH, 'handbook.json')
LOG_FILE = os.path.join(BASE_PATH, 'work_logs.txt')

# --- Firebase 核心處理函數 ---

def load_handbook():
    """讀取手冊資料 (Handbook)"""
    ref = db.reference('handbook')
    data = ref.get()
    if data is None and os.path.exists(HANDBOOK_FILE):
        with open(HANDBOOK_FILE, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
            ref.set(data)
    return data if data else []

def save_handbook(data):
    """儲存手冊資料"""
    db.reference('handbook').set(data)

def load_users():
    """讀取帳號資料 (Users)"""
    ref = db.reference('users')
    data = ref.get()
    if data is None:
        if os.path.exists(USER_FILE):
            with open(USER_FILE, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
        else:
            data = {"admin": "管理員"}
        ref.set(data)
    return data

def save_users(data):
    """儲存帳號資料"""
    db.reference('users').set(data)

def load_logs():
    """讀取歷史紀錄 (Logs)"""
    ref = db.reference('logs')
    data = ref.get()
    if data is None and os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            data = [r.strip() for r in content.split("="*45) if r.strip()]
            ref.set(data)
    return data if data else []

def add_log(entry):
    """新增一筆紀錄到雲端"""
    ref = db.reference('logs')
    logs = ref.get()
    if logs is None: logs = []
    logs.append(entry.strip())
    ref.set(logs)

def calculate_step_probabilities(found_item, step_list):
    """根據手冊項目中記錄的各步驟次數設定計算百分比，確保符合規格並總和為 100%"""
    total_steps = len(step_list)
    if total_steps == 0: return {}
    
    step_counts = found_item.get('step_counts', {})
    total_counts = sum(step_counts.get(step, 0) for step in step_list)
    
    step_stats = {}
    if total_counts > 0:
        for step in step_list:
            cnt = step_counts.get(step, 0)
            prob = round((cnt / total_counts) * 100.0, 1)
            step_stats[step] = {"count": cnt, "prob": prob}
    else:
        base_prob = round(100.0 / total_steps, 1)
        for step in step_list:
            step_stats[step] = {"count": 0, "prob": base_prob}
            
    return step_stats

# --- 登入系統 (維持需要密碼驗證，登入頁不顯示版本) ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

all_users = load_users()

if not st.session_state.logged_in:
    st.title("🛡️ 異常守護者系統 - 系統驗證")
    uid = st.text_input("請輸入工號", type="password")
    if st.button("確認登入", use_container_width=True):
        if uid in all_users:
            st.session_state.logged_in = True
            st.session_state.user_name = all_users[uid]
            st.session_state.uid = uid
            st.rerun()
        else:
            st.error("❌ 此帳號驗證失敗或已被凍結！")
    st.stop()

# --- 主程式介面與統一導航選單調整 ---
st.sidebar.title(f"👤 {st.session_state.user_name}")
st.sidebar.caption(f"版本：{VERSION_SN}")

st.sidebar.markdown("---")
# 將所有導覽選項整合成一個統一的選單，確保點選時能夠精準切換
menu = st.sidebar.selectbox("系統導覽選單", [
    "🔍 異常查詢立案", 
    "📜 歷史回報紀錄", 
    "📊 異常數據統計", 
    "⚙️ 管理後台", 
    "📈 異常紀錄查詢"
])

handbook = load_handbook()
if 'clear_flag' not in st.session_state: st.session_state.clear_flag = 0

# --- 路由分發 ---
if menu == "📈 異常紀錄查詢":
    try:
        import main2
        main2.render_page()
    except Exception as e:
        st.error(f"載入 main2.py 失敗：{e}")

elif menu == "🔍 異常查詢立案":
    st.markdown("""
        <div class="main-header">
            <h2>🛡️ 異常守護者系統 - 專業異常排除中心</h2>
            <p style="margin:0; opacity:0.8;">請輸入相關設備、警報代碼或關鍵字進行智慧檢索與立案處理。</p>
        </div>
    """, unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="query-card">', unsafe_allow_html=True)
        query = st.text_input("🔍 智慧關鍵字檢索", placeholder="例如：馬達、報警、斷線、PLC...", key=f"query_input_{st.session_state.clear_flag}")
        search_trigger = st.button("執行檢索", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    if query or search_trigger:
        search_terms = query.lower().split()
        found_idx = next((i for i, item in enumerate(handbook) if all(t in (str(item.get('keyword','')) + str(item.get('issue',''))).lower() for t in search_terms)), None)
        
        if found_idx is not None:
            found_item = handbook[found_idx]
            st.success(f"📌 **【檢索到的問題描述】**: {found_item['issue']}")
            if found_item.get('order_no'):
                st.info(f"📋 製令編號：{found_item['order_no']}")
            
            img_path = found_item.get('image_path')
            if img_path:
                full_img_path = os.path.join(BASE_PATH, img_path) if not os.path.isabs(img_path) else img_path
                if os.path.exists(full_img_path):
                    st.image(full_img_path, caption="相關附件圖片", width=300)
            
            st.markdown('<div class="solution-box">', unsafe_allow_html=True)
            st.subheader("💡 智慧推薦異常排除方式")
            
            raw_sol = str(found_item.get('solution', ''))
            raw_steps = raw_sol.replace('；', ';').replace('\n', ';').split(';')
            clean_steps = [re.sub(r'^\d+[\.\s]*', '', s.strip()) for s in raw_steps if s.strip()]
            
            probs = calculate_step_probabilities(found_item, clean_steps)
            
            for i, txt in enumerate(clean_steps, 1):
                prob = probs[txt]["prob"]
                if prob >= 100.0:
                    color_style = "color: #2ec4b6; font-weight: bold;"
                elif prob >= 75.0:
                    color_style = "color: #52b788; font-weight: bold;"
                elif prob >= 50.0:
                    color_style = "color: #ffb703; font-weight: bold;"
                elif prob >= 25.0:
                    color_style = "color: #fb8500; font-weight: bold;"
                else:
                    color_style = "color: #8d99ae; font-weight: bold;"
                
                st.markdown(f"&nbsp;&nbsp;<span style='{color_style}'>{i}. {txt}: ({prob}%)</span>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.divider()
            st.subheader("📝 現場處理經過回報")
            extra_fix = st.checkbox("🔄 將此處理經過納入標準排除手法資料庫")
            action = st.text_area("本次實際處理經過記錄 (必填)", key=f"report_input_{st.session_state.clear_flag}")
            
            if st.button("🚀 確認送出並完成立案", use_container_width=True):
                if action.strip():
                    step_counts = found_item.get('step_counts', {})
                    matched_step = None
                    action_lower = action.strip().lower()
                    
                    for idx, step in enumerate(clean_steps):
                        step_lower = step.lower()
                        if (action_lower in step_lower) or (step_lower in action_lower) or (str(idx+1) == action_lower.strip('.')):
                            matched_step = step
                            break
                        keywords = [kw for kw in re.split(r'[\s\u3000\-_、，,]+', step_lower) if len(kw) > 1]
                        if any(kw in action_lower for kw in keywords):
                            matched_step = step
                            break
                    
                    if matched_step:
                        step_counts[matched_step] = step_counts.get(matched_step, 0) + 1
                    else:
                        if clean_steps:
                            first_step = clean_steps[0]
                            step_counts[first_step] = step_counts.get(first_step, 0) + 1
                    
                    found_item['step_counts'] = step_counts

                    if extra_fix:
                        current_steps = clean_steps.copy()
                        if action.strip() not in current_steps:
                            current_steps.append(action.strip())
                        new_formatted_sol = "\n".join([f"{i+1}. {step}" for i, step in enumerate(current_steps)])
                        found_item['solution'] = new_formatted_sol
                    
                    handbook[found_idx] = found_item
                    save_handbook(handbook)
                    
                    log_entry = (f"● 時間：{get_taiwan_time().strftime('%Y-%m-%d %H:%M:%S')}\n"
                                 f"● 人員：{st.session_state.user_name} ({st.session_state.uid})\n"
                                 f"● 問題：{found_item['issue']}\n"
                                 f"● 經過：{action}")
                    add_log(log_entry)
                    
                    st.session_state.clear_flag += 1
                    st.balloons(); st.success("立案成功！次數已同步更新至管理後台與智慧推薦。")
                    st.rerun() 
                else: st.warning("⚠️ 請填寫回報內容後再送出立案")
        elif query: st.error("❌ 找不到符合條件的排除方案，請嘗試其他關鍵字。")

elif menu == "📜 歷史回報紀錄":
    st.header("📜 歷史回報紀錄查詢")
    logs = load_logs()
    if logs:
        display_text = ("\n" + "="*45 + "\n").join(logs)
        st.text_area("歷史紀錄", display_text + "\n" + "="*45, height=600)
    else: st.info("尚無紀錄")

elif menu == "📊 異常數據統計":
    st.markdown('<h2 class="stat-title">📊 異常數據統計</h2>', unsafe_allow_html=True)
    logs = load_logs()
    if logs:
        issues = []
        for rec in logs:
            match = re.search(r"問題[:：]\s*(.*)", rec)
            if match: issues.append(match.group(1).strip())
        
        if issues:
            counts = Counter(issues)
            total_counts = sum(counts.values())
            
            stat_data = []
            for issue_name, cnt in counts.most_common(10):
                pct = round((cnt / total_counts) * 100, 1) if total_counts > 0 else 0.0
                stat_data.append({"異常名稱": issue_name, "次數": cnt, "佔比百分比": f"{pct}%"})
            
            df_stat = pd.DataFrame(stat_data)
            st.table(df_stat)
            
            st.divider()
            st.subheader("⚙️ 統計項目管理 (修改次數與刪除)")
            stat_issues_list = [item["異常名稱"] for item in stat_data]
            selected_stat_issue = st.selectbox("選擇要管理的異常項目", stat_issues_list, key="stat_edit_sel")
            
            current_cnt = counts[selected_stat_issue]
            
            col_edit1, col_edit2 = st.columns(2)
            with col_edit1:
                new_cnt_input = st.number_input("編輯計數次數", value=int(current_cnt), min_value=0, key="edit_cnt_num")
                if st.button("更新次數紀錄", key="update_cnt_btn"):
                    diff = new_cnt_input - current_cnt
                    if diff > 0:
                        for _ in range(diff):
                            add_log(f"● 時間：{get_taiwan_time().strftime('%Y-%m-%d %H:%M:%S')}\n● 人員：{st.session_state.user_name} ({st.session_state.uid})\n● 問題：{selected_stat_issue}\n● 經過：手動補登次數")
                    elif diff < 0:
                        ref_logs = db.reference('logs')
                        curr_logs = ref_logs.get() or []
                        removed = 0
                        new_logs_list = []
                        for r in reversed(curr_logs):
                            if selected_stat_issue in r and removed < abs(diff):
                                removed += 1
                            else:
                                new_logs_list.insert(0, r)
                        ref_logs.set(new_logs_list)
                    st.balloons()
                    st.success("次數更新成功！")
                    st.rerun()
            
            with col_edit2:
                stat_del_pwd = st.text_input("輸入刪除密碼 (0000)", type="password", key="stat_del_p")
                if st.button("刪除此統計項目紀錄", key="stat_del_exec"):
                    if stat_del_pwd == "0000":
                        ref_logs = db.reference('logs')
                        curr_logs = ref_logs.get() or []
                        filtered_logs = [r for r in curr_logs if selected_stat_issue not in r]
                        ref_logs.set(filtered_logs)
                        st.balloons()
                        st.success("已成功刪除該項目的所有相關紀錄！")
                        st.rerun()
                    else:
                        st.error("❌ 刪除密碼錯誤！")
        else: st.info("數據分析中...")
    else: st.info("無紀錄")

elif menu == "⚙️ 管理後台":
    st.header("⚙️ 管理員系統")
    tab1, tab2, tab3 = st.tabs(["➕ 新增手冊項目", "✏️ 編輯手冊清單", "👤 帳號權限管理"])
    
    with tab3:
        st.subheader("👤 人員帳號管理")
        admin_pw = st.text_input("請輸入管理員解鎖密碼", type="password", key="admin_key")
        if admin_pw == "000000":
            st.success("🔒 權限已解鎖")
            st.divider()
            for u_id, u_name in list(all_users.items()):
                col_u, col_b = st.columns([3, 1])
                col_u.write(f"工號：**{u_id}** | 姓名：**{u_name}**")
                if col_b.button(f"🗑️ 刪除", key=f"del_user_{u_id}"):
                    if len(all_users) > 1:
                        del all_users[u_id]
                        save_users(all_users)
                        st.rerun()
            st.divider()
            new_uid = st.text_input("新增工號", key=f"new_uid_{st.session_state.clear_flag}")
            new_uname = st.text_input("人員姓名", key=f"new_uname_{st.session_state.clear_flag}")
            if st.button("確認新增帳號"):
                if new_uid and new_uname:
                    all_users[new_uid] = new_uname
                    save_users(all_users)
                    st.session_state.clear_flag += 1
                    st.rerun()

    with tab1:
        st.subheader("➕ 新增手冊項目")
        n_issue = st.text_input("異常標題", key=f"n_issue_{st.session_state.clear_flag}")
        n_order = st.text_input("製令編號", key=f"n_order_{st.session_state.clear_flag}")
        n_kw = st.text_input("關鍵字", key=f"n_kw_{st.session_state.clear_flag}")
        n_sol = st.text_area("異常排除方式", key=f"n_sol_{st.session_state.clear_flag}")
        n_file = st.file_uploader("夾照片檔", type=["png", "jpg", "jpeg"], key=f"n_file_{st.session_state.clear_flag}")
        
        if st.button("確認新增項目"):
            if n_issue and n_sol:
                image_path = ""
                if n_file is not None:
                    os.makedirs(os.path.join(BASE_PATH, "uploads"), exist_ok=True)
                    image_path = os.path.join("uploads", n_file.name)
                    with open(os.path.join(BASE_PATH, image_path), "wb") as f:
                        f.write(n_file.getbuffer())
                
                handbook.append({
                    "issue": n_issue, 
                    "order_no": n_order, 
                    "keyword": n_kw, 
                    "solution": n_sol,
                    "image_path": image_path,
                    "step_counts": {}
                })
                save_handbook(handbook)
                
                log_entry = (f"● 時間：{get_taiwan_time().strftime('%Y-%m-%d %H:%M:%S')}\n"
                             f"● 人員：{st.session_state.user_name} ({st.session_state.uid})\n"
                             f"● 問題：{n_issue} (後台新增項目)\n"
                             f"● 經過：新增製令編號 [{n_order}] 與異常排除方式")
                add_log(log_entry)
                
                st.session_state.clear_flag += 1
                st.success("新增項目成功！資料已同步至雲端與歷史統計。")
                st.rerun()

    with tab2:
        st.subheader("✏️ 編輯手冊清單")
        search_filter = st.text_input("🔍 輸入關鍵字、標題或製令編號進行模糊篩選", key="edit_filter_input")
        
        filtered_items = []
        for idx, item in enumerate(handbook):
            combined_text = f"{item.get('issue', '')} {item.get('keyword', '')} {item.get('order_no', '')} {item.get('solution', '')}".lower()
            if not search_filter or all(term in combined_text for term in search_filter.lower().split()):
                filtered_items.append((idx, item))
        
        if not filtered_items:
            st.info("查無符合篩選條件的手冊項目")
        
        for i, item in filtered_items:
            with st.expander(f"編輯：{item['issue']} (製令：{item.get('order_no', '無')})"):
                e_issue = st.text_input("標題", item['issue'], key=f"is_{i}")
                e_order = st.text_input("製令編號", item.get('order_no', ''), key=f"ord_{i}")
                e_kw = st.text_input("關鍵字", item.get('keyword', ''), key=f"kw_{i}")
                e_sol = st.text_area("異常排除方式", item['solution'], key=f"sol_{i}", height=200)
                
                st.markdown("---")
                st.subheader("⚙️ 智慧推薦排除方式次數調整")
                raw_steps = e_sol.replace('；', ';').replace('\n', ';').split(';')
                clean_steps = [re.sub(r'^\d+[\.\s]*', '', s.strip()) for s in raw_steps if s.strip()]
                
                current_step_counts = item.get('step_counts', {})
                new_step_counts = {}
                for s_idx, step_txt in enumerate(clean_steps):
                    default_c = current_step_counts.get(step_txt, 0)
                    new_step_counts[step_txt] = st.number_input(f"排除次數 - {s_idx+1}. {step_txt[:20]}...", value=int(default_c), min_value=0, key=f"step_cnt_{i}_{s_idx}")
                
                current_img = item.get('image_path', '')
                if current_img:
                    full_curr_img = os.path.join(BASE_PATH, current_img) if not os.path.isabs(current_img) else current_img
                    if os.path.exists(full_curr_img):
                        st.image(full_curr_img, caption="目前儲存的照片", width=200)
                e_file = st.file_uploader("更換或新增照片檔", type=["png", "jpg", "jpeg"], key=f"efile_{i}")
                
                if st.button("儲存修改", key=f"sv_{i}"):
                    final_img_path = current_img
                    if e_file is not None:
                        os.makedirs(os.path.join(BASE_PATH, "uploads"), exist_ok=True)
                        final_img_path = os.path.join("uploads", e_file.name)
                        with open(os.path.join(BASE_PATH, final_img_path), "wb") as f:
                            f.write(e_file.getbuffer())

                    handbook[i] = {
                        "issue": e_issue, 
                        "order_no": e_order,
                        "keyword": e_kw,
                        "solution": e_sol,
                        "image_path": final_img_path,
                        "step_counts": new_step_counts
                    }
                    save_handbook(handbook)
                    
                    log_entry = (f"● 時間：{get_taiwan_time().strftime('%Y-%m-%d %H:%M:%S')}\n"
                                 f"● 人員：{st.session_state.user_name} ({st.session_state.uid})\n"
                                 f"● 問題：{e_issue} (後台編輯修改)\n"
                                 f"● 經過：修改製令編號 [{e_order}]、關鍵字、照片與異常排除方式內容及次數")
                    add_log(log_entry)
                    
                    st.balloons()
                    st.success("修改成功並已同步記錄至歷史紀錄！")
                
                del_pwd = st.text_input("請輸入刪除密碼 (0000)", type="password", key=f"del_pwd_{i}")
                if st.button("刪除項目", key=f"del_h_{i}"):
                    if del_pwd == "0000":
                        deleted_item = handbook.pop(i)
                        save_handbook(handbook)
                        
                        log_entry = (f"● 時間：{get_taiwan_time().strftime('%Y-%m-%d %H:%M:%S')}\n"
                                     f"● 人員：{st.session_state.user_name} ({st.session_state.uid})\n"
                                     f"● 問題：{deleted_item.get('issue')} (後台刪除項目)\n"
                                     f"● 經過：刪除手冊項目與製令編號 [{deleted_item.get('order_no', '無')}]")
                        add_log(log_entry)
                        
                        st.balloons()
                        st.success("刪除成功並已同步記錄至歷史紀錄！")
                        st.rerun()
                    else:
                        st.error("❌ 刪除密碼錯誤！")

st.sidebar.divider()
if st.sidebar.button("🚪 登出系統"):
    st.session_state.logged_in = False
    st.rerun()
