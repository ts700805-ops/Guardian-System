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
    if 'handbook' in file:
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
            target_records = [r for r in records if f"問題：" in r and issue_name in r]
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
menu = st.sidebar.radio("功能選單", ["🔍 異常查詢與立案", "📜 歷史回報紀錄", "📊 異常數據統計", "⚙️ 管理後台"])

handbook = load_json(HANDBOOK_FILE, [])
all_users = load_json(USER_FILE, {"admin": "管理員"})

# --- 功能 1：查詢與立案 ---
if menu == "🔍 異常查詢與立案":
    st.header("🔍 異常搜尋與立案回報")
    query = st.text_input("輸入關鍵字")
    if query:
        search_terms = query.lower().split()
        found_item = next((item for item in handbook if all(t in (str(item.get('keyword','')) + str(item.get('issue',''))).lower() for t in search_terms)), None)
        if found_item:
            st.success(f"📌 **【問題描述】**: {found_item['issue']}")
            st.subheader("💡 排除建議方案")
            raw_sol = str(found_item.get('solution', ''))
            raw_steps = raw_sol.replace('；', ';').replace('\n', ';').split(';')
            clean_steps = [re.sub(r'
