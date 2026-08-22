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
VERSION_SN = "v2026.08.22-04"  # 程式版本流水號 (日期+版本流水號)
st.set_page_config(page_title=f"異常守護者系統 ({VERSION_SN})", page_icon="🛡️", layout="wide")

# --- 自定義專業排版與頁面底部漸層綠色底色 ---
st.markdown("""
    <style>
    /* 整個頁面主體與底部套用漸層綠色底色 */
    .stApp {
        background: linear-gradient(180deg, #ffffff 0%, #e8f5e9 50%, #c8e6c9 100%);
        background-attachment: fixed;
    }
    .main-header {
        background: linear-gradient(135deg, #1f4068, #162447);
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .query-card {
        background-color: #f8f9fa;
        border-left: 5px solid #00adb5;
        padding: 20px;
        border-radius: 8px;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .solution-box {
        background-color: #e8f4f8;
        padding: 15px;
        border-radius: 6px;
        margin-top: 10px;
        margin-bottom: 15px;
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

def calculate_step_probabilities(issue_name, step_list):
    """根據提供的排除項目數量與雲端紀錄計算推薦機率"""
    total_steps = len(step_list)
    if total_steps == 0: return {}
    
    # 根據提供的排除項目動態計算初始比例 (1項100%、2項各50%...)
    initial_prob = round(100.0 / total_steps, 1)
    step_stats = {step: {"count": 0, "prob": initial_prob} for step in step_list}
    
    logs = load_logs()
    target_records = [r for r in logs if "問題：" in r and issue_name in r]
    total_hits = len(target_records)
    
    if total_hits > 0:
        for rec in target_records:
            action_match = re.search(r"經過[:：]\s*(.*)", rec)
            if action_match:
                action_text = action_match.group(1).strip()
                for step in step_list:
                    if action_text in step or step in action_text:
                        step_stats[step]["count"] += 1
        for step in step_list:
            prob = (step_stats[step]["count"] / total_hits) * 100
            step_stats[step]["prob"] = round(prob, 1)
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

# --- 主程式介面與導航選單調整 ---
st.sidebar.title(f"👤 {st.session_state.user_name}")
st.sidebar.caption(f"版本：{VERSION_SN}")

# 異常排除手冊導航選單
st.sidebar.markdown("---")
menu = st.sidebar.selectbox("異常排除手冊", ["🔍 異常查詢立案", "📜 歷史回報紀錄", "📊 異常數據統計", "⚙️ 管理後台"])

handbook = load_handbook()
if 'clear_flag' not in st.session_state: st.session_state.clear_flag = 0

# --- 功能 1：專業版查詢與立案頁面 ---
if menu == "🔍 異常查詢立案":
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
            if found_item.get('image_path'):
                st.image(found_item['image_path'], caption="相關附件圖片", width=300)
            
            st.markdown('<div class="solution-box">', unsafe_allow_html=True)
            st.subheader("💡 智慧推薦異常排除方式")
            
            raw_sol = str(found_item.get('solution', ''))
            raw_steps = raw_sol.replace('；', ';').replace('\n', ';').split(';')
            clean_steps = [re.sub(r'^\d+[\.\s]*', '', s.strip()) for s in raw_steps if s.strip()]
            
            probs = calculate_step_probabilities(found_item['issue'], clean_steps)
            
            for i, txt in enumerate(clean_steps, 1):
                prob = probs[txt]["prob"]
                if prob >= 80:
                    st.markdown(f"&nbsp;&nbsp;**{i}. {txt}** : :green[({prob}%) 歷史推薦度]")
                elif prob >= 50:
                    st.markdown(f"&nbsp;&nbsp;**{i}. {txt}** : :orange[({prob}%) 歷史推薦度]")
                else:
                    st.markdown(f"&nbsp;&nbsp;**{i}. {txt}** : :blue[({prob}%) 歷史推薦度]")
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.divider()
            st.subheader("📝 現場處理經過回報")
            extra_fix = st.checkbox("🔄 將此處理經過納入標準排除手法資料庫")
            action = st.text_area("本次實際處理經過記錄 (必填)", key=f"report_input_{st.session_state.clear_flag}")
            
            if st.button("🚀 確認送出並完成立案", use_container_width=True):
                if action.strip():
                    if extra_fix:
                        current_steps = clean_steps.copy()
                        if action.strip() not in current_steps:
                            current_steps.append(action.strip())
                        new_formatted_sol = "\n".join([f"{i+1}. {step}" for i, step in enumerate(current_steps)])
                        handbook[found_idx]['solution'] = new_formatted_sol
                        save_handbook(handbook)
                    
                    log_entry = (f"● 時間：{get_taiwan_time().strftime('%Y-%m-%d %H:%M:%S')}\n"
                                 f"● 人員：{st.session_state.user_name} ({st.session_state.uid})\n"
                                 f"● 問題：{found_item['issue']}\n"
                                 f"● 經過：{action}")
                    add_log(log_entry) # 寫入 Firebase
                    
                    st.session_state.clear_flag += 1
                    st.balloons(); st.success("立案成功！資料已同步至雲端資料庫。")
                    st.rerun() 
                else: st.warning("⚠️ 請填寫回報內容後再送出立案")
        elif query: st.error("❌ 找不到符合條件的排除方案，請嘗試其他關鍵字。")

# --- 功能 2：歷史紀錄 ---
elif menu == "📜 歷史回報紀錄":
    st.header("📜 歷史回報紀錄查詢")
    logs = load_logs()
    if logs:
        display_text = ("\n" + "="*45 + "\n").join(logs)
        st.text_area("歷史紀錄", display_text + "\n" + "="*45, height=600)
    else: st.info("尚無紀錄")

# --- 功能 3：數據統計 ---
elif menu == "📊 異常數據統計":
    st.header("📊 異常數據統計")
    logs = load_logs()
    if logs:
        issues = []
        for rec in logs:
            match = re.search(r"問題[:：]\s*(.*)", rec)
            if match: issues.append(match.group(1).strip())
        
        if issues:
            stats = Counter(issues).most_common(10)
            st.table(pd.DataFrame(stats, columns=["異常名稱", "次數"]))
        else: st.info("數據分析中...")
    else: st.info("無紀錄")

# --- 功能 4：管理後台 ---
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
                    "image_path": image_path
                })
                save_handbook(handbook)
                
                # 新增手冊項目時同步寫入歷史紀錄與統計
                log_entry = (f"● 時間：{get_taiwan_time().strftime('%Y-%m-%d %H:%M:%S')}\n"
                             f"● 人員：{st.session_state.user_name} ({st.session_state.uid})\n"
                             f"● 問題：{n_issue} (後台新增項目)\n"
                             f"● 經過：新增製令編號 [{n_order}] 與異常排除方式")
                add_log(log_entry)
                
                st.session_state.clear_flag += 1
                st.success("新增項目成功！資料已同步至雲端與歷史統計。")
                st.rerun()

    with tab2:
        for i, item in enumerate(handbook):
            with st.expander(f"編輯：{item['issue']}"):
                e_issue = st.text_input("標題", item['issue'], key=f"is_{i}")
                e_order = st.text_input("製令編號", item.get('order_no', ''), key=f"ord_{i}")
                e_sol = st.text_area("異常排除方式", item['solution'], key=f"sol_{i}", height=200)
                if st.button("儲存修改", key=f"sv_{i}"):
                    handbook[i] = {
                        "issue": e_issue, 
                        "order_no": e_order,
                        "keyword": item.get('keyword',''), 
                        "solution": e_sol,
                        "image_path": item.get('image_path', '')
                    }
                    save_handbook(handbook)
                    st.rerun()
                if st.button("刪除項目", key=f"del_h_{i}"):
                    handbook.pop(i)
                    save_handbook(handbook)
                    st.rerun()

st.sidebar.divider()
if st.sidebar.button("🚪 登出系統"):
    st.session_state.logged_in = False
    st.rerun()
