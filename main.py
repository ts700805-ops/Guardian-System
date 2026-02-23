import streamlit as st
import json
import os
import datetime
import re
import pandas as pd
from collections import Counter

# --- 基礎設定 ---
st.set_page_config(page_title="異常守護者 2.0 Web", page_icon="🛡️", layout="wide")

# 檔案路徑
USER_FILE = 'users.json'
HANDBOOK_FILE = 'handbook.json'
LOG_FILE = 'work_logs.txt'

# --- 資料讀取函數 ---
def load_json(file, default):
    if os.path.exists(file):
        try:
            with open(file, 'r', encoding='utf-8-sig') as f:
                return json.load(f)
        except: return default
    return default

def save_json(file, data):
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- 邏輯函數 ---
def calculate_probabilities(issue_name, step_list):
    """從紀錄中計算方案成功的機率"""
    if not os.path.exists(LOG_FILE) or not step_list:
        return {step: 0 for step in step_list}
    
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            records = content.split("="*45)
            target_records = [r for r in records if f"問題" in r and issue_name in r]
            total_hits = len(target_records)
            
            step_stats = {step: 0 for step in step_list}
            if total_hits > 0:
                for rec in target_records:
                    action_match = re.search(r"經過[:：]\s*(.*)", rec)
                    if action_match:
                        action_text = action_match.group(1).strip()
                        for step in step_list:
                            if action_text in step or step in action_text:
                                step_stats[step] += 1
                return {step: round((step_stats[step]/total_hits)*100, 1) for step in step_list}
    except: pass
    return {step: 0 for step in step_list}

# --- 登入系統 ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🛡️ 異常守護者：系統安全驗證")
    users = load_json(USER_FILE, {})
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
menu = st.sidebar.radio("功能選單", ["🔍 異常查詢與立案", "📜 歷史回報紀錄", "📊 數據分析報表", "⚙️ 管理員後台"])

# 讀取資料
handbook = load_json(HANDBOOK_FILE, [])

# --- 功能 1：查詢與立案 ---
if menu == "🔍 異常查詢與立案":
    st.header("🔍 異常搜尋與處理回報")
    query = st.text_input("請輸入關鍵字（例如：馬達、感測器）")
    
    if query:
        search_terms = query.lower().split()
        found_item = next((item for item in handbook if all(t in (str(item.get('keyword',''))+str(item.get('issue',''))).lower() for t in search_terms)), None)
        
        if found_item:
            st.success(f"📌 問題描述：{found_item['issue']}")
            st.session_state.current_issue = found_item['issue']
            
            # 顯示建議方案
            st.subheader("💡 排除建議方案")
            raw_steps = str(found_item.get('solution', '')).replace('；', ';').replace('\n', ';').split(';')
            clean_steps = [re.sub(r'^\d+[\.\s]*', '', s.strip()) for s in raw_steps if s.strip()]
            
           probs = calculate_probabilities(found_item['issue'], clean_steps)

for i, step in enumerate(clean_steps, 1):
    p = probs.get(step, 0)
    
    # 根據機率決定顏色
    if p >= 80:
        color = "green"
    elif p >= 50:
        color = "orange"
    else:
        color = "blue"
    
    # 使用 st.markdown 配合 :顏色[文字] 語法來顯色
    st.markdown(f"{i}. {step} : {color}[({p}%) 推薦度]")
            
            st.divider()
            
            # 立案回報區
            st.subheader("📝 處理經過回報")
            action = st.text_input("請輸入本次處理經過 (必填)")
            add_to_handbook = st.checkbox("將此次回報內容新增為此異常的排除方式")
            
            if st.button("完成立案"):
                if action:
                    # 更新手冊
                    if add_to_handbook:
                        found_item['solution'] = found_item.get('solution','') + ";" + action
                        save_json(HANDBOOK_FILE, handbook)
                    
                    # 寫入 Log
                    log_entry = (f"● 時間：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                                 f"● 人員：{st.session_state.user_name} ({st.session_state.uid})\n"
                                 f"● 問題：{found_item['issue']}\n"
                                 f"● 經過：{action}\n" + "="*45 + "\n")
                    with open(LOG_FILE, 'a', encoding='utf-8') as f:
                        f.write(log_entry)
                    
                    st.balloons()
                    st.toast("立案成功！紀錄已存入雲端。")
                else:
                    st.warning("請填寫處理經過！")
        else:
            st.error("❌ 找不到相關方案")

# --- 功能 2：歷史紀錄 ---
elif menu == "📜 歷史回報紀錄":
    st.header("📜 歷史回報紀錄")
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            st.text_area("所有立案紀錄", f.read(), height=500)
    else:
        st.info("尚無紀錄")

# --- 功能 3：統計報表 ---
elif menu == "📊 數據分析報表":
    st.header("🔥 近期熱門異常排行榜")
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            issues = re.findall(r"問題[:：]\s*(.*)", content)
            if issues:
                stats = Counter(issues).most_common(10)
                df = pd.DataFrame(stats, columns=["異常問題名稱", "發生次數"])
                st.table(df)
            else:
                st.info("尚未有足夠數據生成報表")

# --- 功能 4：管理員後台 ---
elif menu == "⚙️ 管理員後台":
    st.header("⚙️ 排除手法管理後台")
    
    # 新增項目
    with st.expander("➕ 新增異常項目"):
        new_issue = st.text_input("異常標題")
        new_kw = st.text_input("關鍵字")
        new_sol = st.text_area("排除步驟 (用分號 ; 分隔)")
        if st.button("確認新增"):
            handbook.append({"issue": new_issue, "keyword": new_kw, "solution": new_sol})
            save_json(HANDBOOK_FILE, handbook)
            st.success("已新增！")
            st.rerun()

    # 編輯與刪除
    st.subheader("✏️ 現有清單編輯")
    for i, item in enumerate(handbook):
        col1, col2 = st.columns([4, 1])
        with col1:
            with st.expander(f"{i+1}. {item['issue']}"):
                edit_issue = st.text_input("標題", item['issue'], key=f"is_{i}")
                edit_kw = st.text_input("關鍵字", item['keyword'], key=f"kw_{i}")
                edit_sol = st.text_area("方案", item['solution'], key=f"sol_{i}")
                if st.button("儲存修改", key=f"save_{i}"):
                    handbook[i] = {"issue": edit_issue, "keyword": edit_kw, "solution": edit_sol}
                    save_json(HANDBOOK_FILE, handbook)
                    st.rerun()
        with col2:
            if st.button("🗑️ 刪除", key=f"del_{i}"):
                handbook.pop(i)
                save_json(HANDBOOK_FILE, handbook)
                st.rerun()

st.sidebar.divider()
if st.sidebar.button("登出系統"):
    st.session_state.logged_in = False
    st.rerun()
