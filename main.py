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
    # 自動備份邏輯
    try:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        dst = os.path.join(BACKUP_DIR, f'handbook_backup_{timestamp}.json')
        shutil.copy2(file, dst)
    except: pass

def calculate_step_probabilities(issue_name, step_list):
    """計算方案推薦度 (移植並優化 Tkinter 版本邏輯)"""
    total_steps = len(step_list)
    if total_steps == 0: return {}
    initial_prob = round(100 / total_steps, 1)
    step_stats = {step: {"count": 0, "prob": initial_prob} for step in step_list}
    
    if not os.path.exists(LOG_FILE): return step_stats
    
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            records = content.split("="*45)
            # 確保精確比對問題名稱
            target_records = [r for r in records if f"問題：" in r and issue_name in r]
            total_hits = len(target_records)
            
            if total_hits > 0:
                for rec in target_records:
                    action_match = re.search(r"經過[:：]\s*(.*)", rec)
                    if action_match:
                        action_text = action_match.group(1).strip()
                        for step in step_list:
                            # 模糊比對：判斷回報的經過是否包含建議步驟的關鍵字
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
    users = load_json(USER_FILE, {"admin": "管理員"}) # 預設 admin 帳號
    uid = st.text_input("請輸入工號", type="password", help="請輸入您的系統驗證碼")
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
st.sidebar.info(f"工號：{st.session_state.uid}")
menu = st.sidebar.radio("功能選單", ["🔍 異常查詢與立案", "📜 歷史回報紀錄", "📊 異常數據統計", "⚙️ 管理後台"])

handbook = load_json(HANDBOOK_FILE, [])

# --- 功能 1：查詢與立案 ---
if menu == "🔍 異常查詢與立案":
    st.header("🔍 異常搜尋與立案回報")
    query = st.text_input("輸入關鍵字 (例如：馬達、皮帶、斷線)", placeholder="請輸入異常狀況關鍵字...")
    
    if query:
        search_terms = query.lower().split()
        found_item = next((item for item in handbook if all(t in (str(item.get('keyword','')) + str(item.get('issue',''))).lower() for t in search_terms)), None)
        
        if found_item:
            st.success(f"📌 **【問題描述】**: {found_item['issue']}")
            st.subheader("💡 排除建議方案")
            
            # 解析方案步驟
            raw_sol = str(found_item.get('solution', ''))
            raw_steps = raw_sol.replace('；', ';').replace('\n', ';').split(';')
            clean_steps = [re.sub(r'^\d+[\.\s]*', '', s.strip()) for s in raw_steps if s.strip()]
            
            probs = calculate_step_probabilities(found_item['issue'], clean_steps)
            
            # 建立美化的建議清單
            for i, txt in enumerate(clean_steps, 1):
                prob = probs[txt]["prob"]
                if prob >= 80: color, status = "green", "[🔥 強烈推薦]"
                elif prob >= 50: color, status = "orange", "[✅ 建議嘗試]"
                elif prob > 0: color, status = "blue", "[ℹ️ 參考方案]"
                else: color, status = "violet", "[🆕 可測試]"
                
                st.markdown(f"**{i}. {txt}** \n:{color}[成功機率約 {prob}% {status}]")
            
            st.divider()
            
            # 立案回報區
            st.subheader("📝 處理經過回報")
            col_cb, col_in = st.columns([1, 1])
            with col_cb:
                extra_fix = st.checkbox("🔄 將此回報更新至排除手法")
            
            action = st.text_area("本次處理經過 (必填)", placeholder="描述您是如何解決此問題的...", height=100)
            
            if st.button("🚀 完成立案", use_container_width=True):
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
                    
                    st.balloons()
                    st.toast("立案成功！資料已同步雲端。")
                    st.info("已清空當前查詢，可進行下一次搜尋。")
                else:
                    st.warning("⚠️ 請務必填寫處理經過！")
        else:
            st.error("❌ 找不到相關方案，請嘗試其他關鍵字或聯繫管理員新增。")

# --- 功能 2：歷史紀錄 ---
elif menu == "📜 歷史回報紀錄":
    st.header("📜 歷史回報紀錄查詢")
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            # 將 Log 反向排序，讓最新的紀錄在最上面
            records = content.split("="*45)
            records = [r.strip() for r in records if r.strip()]
            records.reverse()
            
            st.text_area("歷史紀錄 (最新排至最舊)", "\n\n".join(records), height=600)
    else:
        st.info("尚無紀錄資料")

# --- 功能 3：數據統計 ---
elif menu == "📊 異常數據統計":
    st.header("📊 異常數據自動化統計")
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            issues = re.findall(r"問題[:：]\s*(.*)", content)
            if issues:
                stats = Counter(issues).most_common(10)
                df = pd.DataFrame(stats, columns=["異常名稱", "發生次數"])
                
                # 顯示圖表
                st.subheader("🔥 近期 Top 10 熱門異常")
                st.bar_chart(df.set_index("異常名稱"))
                
                # 顯示表格
                st.table(df)
            else:
                st.info("數據不足，無法生成報表。")
    else:
        st.info("尚未建立 Log 檔案。")

# --- 功能 4：管理後台 ---
elif menu == "⚙️ 管理後台":
    st.header("⚙️ 排除手法管理系統")
    
    tab1, tab2 = st.tabs(["➕ 新增異常項目", "✏️ 編輯現有清單"])
    
    with tab1:
        with st.form("new_issue_form"):
            n_issue = st.text_input("異常標題 (例：XY軸馬達異常)")
            n_kw = st.text_input("搜尋關鍵字 (多個請用空格分開)")
            n_sol = st.text_area("排除步驟 (建議用分號 ; 分隔)")
            if st.form_submit_button("確認新增"):
                if n_issue and n_sol:
                    handbook.append({"issue": n_issue, "keyword": n_kw, "solution": n_sol})
                    save_json(HANDBOOK_FILE, handbook)
                    st.success("✅ 已成功新增項目！")
                    st.rerun()
                else:
                    st.error("標題與方案為必填項。")

    with tab2:
        search_edit = st.text_input("🔍 快速搜尋要修改的項目", placeholder="輸入標題關鍵字...")
        filtered_handbook = [(i, item) for i, item in enumerate(handbook) if not search_edit or search_edit.lower() in item['issue'].lower()]
        
        for i, item in filtered_handbook:
            with st.expander(f"編輯：{item['issue']}"):
                e_issue = st.text_input("標題", item['issue'], key=f"is_{i}")
                e_kw = st.text_input("關鍵字", item['keyword'], key=f"kw_{i}")
                e_sol = st.text_area("方案內容", item['solution'], key=f"sol_{i}", height=150)
                
                col_save, col_del = st.columns(2)
                if col_save.button("💾 儲存修改", key=f"sv_{i}", use_container_width=True):
                    handbook[i] = {"issue": e_issue, "keyword": e_kw, "solution": e_sol}
                    save_json(HANDBOOK_FILE, handbook)
                    st.success("已儲存")
                    st.rerun()
                if col_del.button("🗑️ 刪除此項", key=f"del_{i}", use_container_width=True):
                    handbook.pop(i)
                    save_json(HANDBOOK_FILE, handbook)
                    st.warning("項目已刪除")
                    st.rerun()

st.sidebar.divider()
if st.sidebar.button("🚪 登出系統", use_container_width=True):
    st.session_state.logged_in = False
    st.rerun()
