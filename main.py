import streamlit as st
import json
import os
import datetime
import re
import pandas as pd
import shutil
from collections import Counter

# --- 基礎設定 ---
st.set_page_config(page_title="異常守護者 1.0版 Web", page_icon="🛡️", layout="wide")

# 檔案路徑設定
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
USER_FILE = os.path.join(BASE_PATH, 'users.json')
HANDBOOK_FILE = os.path.join(BASE_PATH, 'handbook.json')
LOG_FILE = os.path.join(BASE_PATH, 'work_logs.txt')
BACKUP_DIR = os.path.join(BASE_PATH, 'backup')

if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

# --- 核心函數 ---
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
    try:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        dst = os.path.join(BACKUP_DIR, f'handbook_backup_{timestamp}.json')
        shutil.copy2(file, dst)
    except: pass

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
            target_records = [r for r in records if "問題" in r and issue_name in r]
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

if not st.session_state.logged_in:
    st.title("🛡️ 異常守護者 系統安全驗證")
    users = load_json(USER_FILE, {"admin": "管理員"})
    uid = st.text_input("請輸入工號", type="password")
    if st.button("確認登入"):
        if uid in users:
            st.session_state.logged_in = True
            st.session_state.user_name = users[uid]
            st.session_state.uid = uid
            st.rerun()
        else:
            st.error("驗證失敗，工號錯誤！")
    st.stop()

# --- 主程式介面 ---
st.sidebar.title(f"👤 {st.session_state.user_name}")
menu = st.sidebar.radio("功能選單", ["🔍 異常查詢與立案", "📜 歷史回報紀錄", "📊 異常數據統計", "⚙️ 管理後台"])

handbook = load_json(HANDBOOK_FILE, [])

# --- 功能 1：查詢與立案 ---
if menu == "🔍 異常查詢與立案":
    st.header("🔍 異常搜尋與立案回報")
    query = st.text_input("關鍵字搜尋")
    
    if query:
        search_terms = query.lower().split()
        found_item = next((item for item in handbook if all(t in (str(item.get('keyword','')) + str(item.get('issue',''))).lower() for t in search_terms)), None)
        
        if found_item:
            st.success(f"📌 **【問題描述】**: {found_item['issue']}")
            st.subheader("💡 排除建議方案")
            
            raw_sol = str(found_item.get('solution', ''))
            raw_steps = raw_sol.replace('；', ';').replace('\n', ';').split(';')
            clean_steps = [re.sub(r'^\d+[\.\s]*', '', s.strip()) for s in raw_steps if s.strip()]
            
            probs = calculate_step_probabilities(found_item['issue'], clean_steps)
            
            for i, txt in enumerate(clean_steps, 1):
                prob = probs[txt]["prob"]
                if prob >= 80: color, status = "green", "[強烈推薦]"
                elif prob >= 50: color, status = "orange", "[建議嘗試]"
                elif prob > 0: color, status = "blue", "[參考方案]"
                else: color, status = "violet", "[可測試]"
                
                # 修正顏色標籤顯示問題
                st.markdown(f"{i}. {txt} :{color}[({prob}%) {status}]")
            
            st.divider()
            st.subheader("📝 處理經過回報")
            extra_fix = st.checkbox("將此次回報內容新增為此異常的排除方式")
            action = st.text_input("請輸入本次處理經過 (必填)")
            
            if st.button("完成立案"):
                if action:
                    if extra_fix:
                        current_sol = found_item.get('solution', '').strip()
                        found_item['solution'] = current_sol + (";" if current_sol else "") + action
                        save_json(HANDBOOK_FILE, handbook)
                    
                    log_entry = (f"● 時間：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                                 f"● 人員：{st.session_state.user_name} ({st.session_state.uid})\n"
                                 f"● 問題：{found_item['issue']}\n"
                                 f"● 經過：{action}\n" + "="*45 + "\n")
                    with open(LOG_FILE, 'a', encoding='utf-8') as f:
                        f.write(log_entry)
                    st.success("立案成功！")
                else:
                    st.warning("請填寫處理經過！")
        else:
            st.error("❌ 找不到相關方案")

# --- 功能 2：歷史紀錄 ---
elif menu == "📜 歷史回報紀錄":
    st.header("📜 歷史回報紀錄查詢")
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            st.text_area("詳細歷史紀錄", f.read(), height=600)
    else:
        st.info("尚無紀錄資料")

# --- 功能 3：數據統計 ---
elif menu == "📊 異常數據統計":
    st.header("🔥 近期熱門異常排行榜")
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            issues = re.findall(r"問題[:：]\s*(.*)", content)
            if issues:
                stats = Counter(issues).most_common(10)
                st.table(pd.DataFrame(stats, columns=["異常問題名稱", "發生次數"]))
            else:
                st.info("尚無數據")
    else:
        st.info("尚未建立紀錄檔")

# --- 功能 4：管理後台 ---
elif menu == "⚙️ 管理後台":
    st.header("⚙️ 排除手法管理")
    with st.expander("➕ 新增異常項目"):
        n_issue = st.text_input("異常標題")
        n_kw = st.text_input("搜尋關鍵字")
        n_sol = st.text_area("排除步驟 (用分號 ; 分隔)")
        if st.button("確認新增"):
            handbook.append({"issue": n_issue, "keyword": n_kw, "solution": n_sol})
            save_json(HANDBOOK_FILE, handbook)
            st.rerun()

    for i, item in enumerate(handbook):
        with st.expander(f"{i+1}. {item['issue']}"):
            e_issue = st.text_input("標題", item['issue'], key=f"is_{i}")
            e_kw = st.text_input("關鍵字", item['keyword'], key=f"kw_{i}")
            e_sol = st.text_area("方案內容", item['solution'], key=f"sol_{i}")
            if st.button("儲存修改", key=f"sv_{i}"):
                handbook[i] = {"issue": e_issue, "keyword": e_kw, "solution": e_sol}
                save_json(HANDBOOK_FILE, handbook)
                st.rerun()
            if st.button("🗑️ 刪除項目", key=f"del_{i}"):
                handbook.pop(i)
                save_json(HANDBOOK_FILE, handbook)
                st.rerun()

if st.sidebar.button("登出系統"):
    st.session_state.logged_in = False
    st.rerun()
