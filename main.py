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
st.sidebar.
