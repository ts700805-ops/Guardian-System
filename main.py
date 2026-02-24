import streamlit as st
import json
import os
import datetime
import re
import pandas as pd
import shutil
from collections import Counter
import firebase_admin
from firebase_admin import credentials, db

# --- 基礎設定 ---
st.set_page_config(page_title="大量科技異常守護者系統", page_icon="🛡️", layout="wide")

# --- Firebase 初始化 ---
if not firebase_admin._apps:
    try:
        # 從 Streamlit Secrets 讀取金鑰與網址
        fb_creds = json.loads(st.secrets["firebase"]["service_account"])
        fb_url = st.secrets["firebase"]["databaseURL"]
        
        cred = credentials.Certificate(fb_creds)
        firebase_admin.initialize_app(cred, {
            'databaseURL': fb_url
        })
    except Exception as e:
        st.error(f"Firebase 初始化失敗：{e}")

# 獲取台灣時間 (UTC+8)
def get_taiwan_time():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))

# 檔案路徑設定
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
USER_FILE = os.path.join(BASE_PATH, 'users.json')
HANDBOOK_FILE = os.path.join(BASE_PATH, 'handbook.json')
LOG_FILE = os.path.join(BASE_PATH, 'work_logs.txt')

# --- Firebase 資料處理函數 ---
def load_handbook():
    """從 Firebase 讀取資料，若無資料則嘗試從本地 JSON 匯入"""
    try:
        ref = db.reference('handbook')
        data = ref.get()
        if data is None:
            # 如果 Firebase 是空的，讀取本地舊檔案並上傳
            if os.path.exists(HANDBOOK_FILE):
                with open(HANDBOOK_FILE, 'r', encoding='utf-8-sig') as f:
                    local_data = json.load(f)
                    ref.set(local_data)
                    return local_data
            return []
        return data
    except:
        return []

def save_handbook(data):
    """同步資料到 Firebase"""
    try:
        ref = db.reference('handbook')
        ref.set(data)
        return True
    except:
        return False

# --- 基礎 JSON 讀寫 (用於帳號) ---
def load_json(file, default):
    if os.path.exists(file):
        try:
            with open(file, 'r', encoding='utf-8-sig') as f:
                content = json.load(f)
                return content if content else default
        except: return default
    return default

def save_json(file, data):
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def calculate_step_probabilities(issue_name, step_list):
    total_steps = len(step_list)
    if total_steps == 0: return {}
    initial_prob = round(100 / total_steps, 1)
    step_stats = {step: {"count": 0, "prob": initial_prob} for step in step_list}
    if not os.path.exists(LOG_FILE): return step_stats
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            records = content.split("="*45)
            target_records = [r for r in records if "問題：" in r and issue_name in r]
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
    except: return step_stats

# --- 登入系統 ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

users = load_json(USER_FILE, {"admin": "管理員"}) 

if not st.session_state.logged_in:
    st.title("🛡️ 大量科技異常守護者系統 系統驗證")
    uid = st.text_input("請輸入工號", type="password")
    if st.button("確認登入", use_container_width=True):
        if uid in users:
            st.session_state.logged_in = True
            st.session_state.user_name = users[uid]
            st.session_state.uid = uid
            st.rerun()
        else:
            st.error("❌ 驗證失敗，工號錯誤！")
    st.stop()

# --- 主程式介面 ---
st.sidebar.title(f"👤 {st.session_state.user_name}")
menu = st.sidebar.radio("功能選單", ["🔍 大量科技異常守護者系統", "📜 歷史回報紀錄", "📊 異常數據統計", "⚙️ 管理後台"])

# 【核心改變】資料從 Firebase 載入
handbook = load_handbook()
all_users = load_json(USER_FILE, {"admin": "管理員"})

if 'clear_flag' not in st.session_state: st.session_state.clear_flag = 0

# --- 功能 1：查詢與立案 ---
if menu == "🔍 大量科技異常守護者系統":
    st.header("🛡️ 大量科技異常守護者系統")
    query = st.text_input("輸入關鍵字進行搜尋", placeholder="例如：馬達, 報警, 斷線...", key=f"query_input_{st.session_state.clear_flag}")
    search_trigger = st.button("🔍 開始查詢", use_container_width=True)
    
    if query or search_trigger:
        search_terms = query.lower().split()
        found_idx = next((i for i, item in enumerate(handbook) if all(t in (str(item.get('keyword','')) + str(item.get('issue',''))).lower() for t in search_terms)), None)
        
        if found_idx is not None:
            found_item = handbook[found_idx]
            st.success(f"📌 **【問題描述】**: {found_item['issue']}")
            st.subheader("💡 排除建議方案")
            
            raw_sol = str(found_item.get('solution', ''))
            raw_steps = raw_sol.replace('；', ';').replace('\n', ';').split(';')
            clean_steps = [re.sub(r'^\d+[\.\s]*', '', s.strip()) for s in raw_steps if s.strip()]
            
            probs = calculate_step_probabilities(found_item['issue'], clean_steps)
            
            for i, txt in enumerate(clean_steps, 1):
                prob = probs[txt]["prob"]
                color = "green" if prob >= 80 else ("orange" if prob >= 50 else "blue")
                st.markdown(f"**{i}. {txt}** :{color}[({prob}%) 推薦度]")
            
            st.divider()
            st.subheader("📝 處理經過回報")
            extra_fix = st.checkbox("🔄 將此回報更新至排除手法")
            action = st.text_area("本次處理經過 (必填)", key=f"report_input_{st.session_state.clear_flag}")
            
            if st.button("🚀 完成立案", use_container_width=True):
                if action.strip():
                    if extra_fix:
                        current_steps = clean_steps.copy()
                        if action.strip() not in current_steps:
                            current_steps.append(action.strip())
                        new_formatted_sol = "\n".join([f"{i+1}. {step}" for i, step in enumerate(current_steps)])
                        handbook[found_idx]['solution'] = new_formatted_sol
                        save_handbook(handbook) # 同步到 Firebase
                    
                    log_entry = (f"● 時間：{get_taiwan_time().strftime('%Y-%m-%d %H:%M:%S')}\n"
                                 f"● 人員：{st.session_state.user_name} ({st.session_state.uid})\n"
                                 f"● 問題：{found_item['issue']}\n"
                                 f"● 經過：{action}\n" + "="*45 + "\n")
                    with open(LOG_FILE, 'a', encoding='utf-8') as f: f.write(log_entry)
                    
                    st.session_state.clear_flag += 1
                    st.balloons(); st.success("立案成功！資料已即時同步至雲端。")
                    st.rerun() 
                else: st.warning("⚠️ 請填寫回報內容")
        elif query: st.error("❌ 找不到方案")

# --- 歷史紀錄與統計 (保持不變) ---
elif menu == "📜 歷史回報紀錄":
    st.header("📜 歷史回報紀錄查詢")
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            st.text_area("歷史紀錄", f.read(), height=600)
    else: st.info("尚無紀錄")

elif menu == "📊 異常數據統計":
    st.header("📊 數據統計")
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            issues = re.findall(r"問題[:：]\s*(.*)", content)
            if issues:
                stats = Counter(issues).most_common(10)
                st.table(pd.DataFrame(stats, columns=["異常名稱", "次數"]))
            else: st.info("數據不足")
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
                        save_json(USER_FILE, all_users)
                        st.rerun()
            st.divider()
            new_uid = st.text_input("新增工號", key=f"new_uid_{st.session_state.clear_flag}")
            new_uname = st.text_input("人員姓名", key=f"new_uname_{st.session_state.clear_flag}")
            if st.button("確認新增帳號"):
                if new_uid and new_uname:
                    all_users[new_uid] = new_uname
                    save_json(USER_FILE, all_users)
                    st.session_state.clear_flag += 1
                    st.rerun()

    with tab1:
        st.subheader("➕ 新增手冊項目")
        n_issue = st.text_input("異常標題", key=f"n_issue_{st.session_state.clear_flag}")
        n_kw = st.text_input("關鍵字", key=f"n_kw_{st.session_state.clear_flag}")
        n_sol = st.text_area("方案內容", key=f"n_sol_{st.session_state.clear_flag}")
        if st.button("確認新增項目"):
            if n_issue and n_sol:
                handbook.append({"issue": n_issue, "keyword": n_kw, "solution": n_sol})
                save_handbook(handbook) # 同步到 Firebase
                st.session_state.clear_flag += 1
                st.rerun()

    with tab2:
        for i, item in enumerate(handbook):
            with st.expander(f"編輯：{item['issue']}"):
                e_issue = st.text_input("標題", item['issue'], key=f"is_{i}")
                e_sol = st.text_area("方案", item['solution'], key=f"sol_{i}", height=200)
                if st.button("儲存修改", key=f"sv_{i}"):
                    handbook[i] = {"issue": e_issue, "keyword": item['keyword'], "solution": e_sol}
                    save_handbook(handbook) # 同步到 Firebase
                    st.rerun()
                if st.button("刪除項目", key=f"del_h_{i}"):
                    handbook.pop(i)
                    save_handbook(handbook) # 同步到 Firebase
                    st.rerun()

st.sidebar.divider()
if st.sidebar.button("🚪 登出系統"):
    st.session_state.logged_in = False
    st.rerun()
