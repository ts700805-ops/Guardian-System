import tkinter as tk
from tkinter import messagebox, ttk
import json
import datetime
import os
import re
import shutil
from collections import Counter

class GuardianApp:
    def __init__(self, root):
        self.root = root
        self.root.title("異常守護者 1.0版")
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        
        # 建立備份資料夾
        self.backup_path = os.path.join(self.base_path, 'backup')
        if not os.path.exists(self.backup_path):
            os.makedirs(self.backup_path)
            
        self.users = self.safe_load('users.json', {})
        self.handbook = self.safe_load('handbook.json', [])
        self.current_user = None
        self.current_issue = None
        self.current_uid = None
        self.found_item_ref = None
        self.editing_index = None

        self.root.withdraw()
        self.show_login_gate()

    def safe_load(self, filename, default):
        path = os.path.join(self.base_path, filename)
        if not os.path.exists(path): return default
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                content = json.load(f)
                return content if content else default
        except: return default

    def auto_backup_data(self):
        try:
            src = os.path.join(self.base_path, 'handbook.json')
            if os.path.exists(src):
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                dst = os.path.join(self.backup_path, f'handbook_backup_{timestamp}.json')
                shutil.copy2(src, dst)
        except: pass 

    def show_login_gate(self):
        self.gate = tk.Toplevel()
        self.gate.title("系統安全驗證")
        self.gate.geometry("350x200")
        gw, gh = 350, 200
        gx = (self.gate.winfo_screenwidth() - gw) // 2
        gy = (self.gate.winfo_screenheight() - gh) // 2
        self.gate.geometry(f"{gw}x{gh}+{gx}+{gy}")
        self.gate.protocol("WM_DELETE_WINDOW", self.root.destroy)
        tk.Label(self.gate, text="異常守護者 系統登入", font=("Arial", 14, "bold"), pady=20).pack()
        input_frame = tk.Frame(self.gate)
        input_frame.pack(pady=5)
        tk.Label(input_frame, text="請輸入工號: ").pack(side="left")
        self.gate_id_entry = tk.Entry(input_frame, font=("Arial", 12), width=15)
        self.gate_id_entry.pack(side="left")
        self.gate_id_entry.focus_set()
        self.gate_id_entry.bind('<Return>', lambda e: self.verify_gate_login())
        tk.Button(self.gate, text="確認登入", font=("Arial", 11, "bold"), 
                  bg="#2C3E50", fg="white", width=20, command=self.verify_gate_login).pack(pady=20)

    def verify_gate_login(self):
        uid = self.gate_id_entry.get().strip()
        if uid in self.users:
            self.current_user = self.users[uid]
            self.current_uid = uid
            self.gate.destroy() 
            self.show_welcome_effect()
        else:
            messagebox.showerror("驗證失敗", "工號錯誤，請聯繫管理員！")

    def show_welcome_effect(self):
        welcome_win = tk.Toplevel(self.root)
        welcome_win.overrideredirect(True) 
        welcome_win.attributes("-topmost", True)
        welcome_win.config(bg="#27AE60")
        ww, wh = 300, 80
        wx = (welcome_win.winfo_screenwidth() - ww) // 2
        wy = (welcome_win.winfo_screenheight() - wh) // 2
        welcome_win.geometry(f"{ww}x{wh}+{wx}+{wy}")
        tk.Label(welcome_win, text=f"歡迎回來，{self.current_user}！", 
                 font=("Arial", 14, "bold"), fg="white", bg="#27AE60", pady=25).pack()
        def fade_out():
            welcome_win.destroy()
            self.init_main_app()
        welcome_win.after(1500, fade_out)

    def init_main_app(self):
        self.setup_ui()     
        self.root.update_idletasks()
        w, h = 550, 820 # 微調視窗高度
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.deiconify()

    def save_handbook(self):
        path = os.path.join(self.base_path, 'handbook.json')
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.handbook, f, ensure_ascii=False, indent=4)
            self.auto_backup_data() 
            return True
        except Exception as e:
            messagebox.showerror("錯誤", f"儲存失敗: {e}")
            return False

    def setup_ui(self):
        tk.Label(self.root, text="異常守護者 1.0版", font=("Arial", 18, "bold"), 
                 bg="#2C3E50", fg="white", pady=10).pack(fill="x")

        status_frame = tk.Frame(self.root, pady=5)
        status_frame.pack(padx=20, fill="x")
        self.name_label = tk.Label(status_frame, text=f"當前人員：{self.current_user} ({self.current_uid})", 
                                   font=("Arial", 12, "bold"), fg="#2C3E50")
        self.name_label.pack(side="left")
        tk.Button(status_frame, text="管理後台", command=self.open_admin, bg="#95a5a6", fg="white").pack(side="right")

        search_frame = tk.LabelFrame(self.root, text=" 異常搜尋 ", padx=10, pady=10)
        search_frame.pack(padx=20, pady=10, fill="x")
        tk.Label(search_frame, text="關鍵字:").pack(side="left")
        self.query_entry = tk.Entry(search_frame)
        self.query_entry.pack(side="left", fill="x", expand=True, padx=5)
        tk.Button(search_frame, text="搜尋方案", command=self.search_issue, bg="#4CAF50", fg="white").pack(side="right")

        tk.Label(self.root, text="[ 排除建議方案 ]", font=("Arial", 10, "bold")).pack(anchor="w", padx=20)
        res_box = tk.Frame(self.root, bd=1, relief="solid")
        res_box.pack(padx=20, pady=5, fill="x")
        scrollbar = tk.Scrollbar(res_box)
        scrollbar.pack(side="right", fill="y")
        self.result_display = tk.Text(res_box, font=("Arial", 12), padx=10, pady=10, spacing1=5, 
                                      yscrollcommand=scrollbar.set, height=10)
        self.result_display.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.result_display.yview)
        
        self.result_display.tag_config("high", foreground="#1B5E20", font=("Arial", 12, "bold"))  
        self.result_display.tag_config("mid", foreground="#E67E22", font=("Arial", 12, "bold"))   
        self.result_display.tag_config("low", foreground="#2ECC71", font=("Arial", 12, "bold"))   
        self.result_display.tag_config("new", foreground="#2980B9", font=("Arial", 12, "bold"))   
        self.result_display.tag_config("bold", font=("Arial", 12, "bold"))
        self.result_display.config(state="disabled")

        self.extra_fix_var = tk.BooleanVar()
        tk.Checkbutton(self.root, text="將此次回報內容新增為此異常的排除方式", 
                       variable=self.extra_fix_var, font=("Arial", 10, "bold"), fg="#E67E22").pack(anchor="w", padx=20, pady=5)

        tk.Label(self.root, text="處理經過回報 (必填):", font=("Arial", 10, "bold")).pack(anchor="w", padx=20)
        self.action_entry = tk.Entry(self.root, font=("Arial", 12))
        self.action_entry.pack(padx=20, pady=5, fill="x", ipady=8)

        btn_container = tk.Frame(self.root)
        btn_container.pack(padx=20, pady=10, fill="x")
        tk.Button(btn_container, text="完成立案並清空", font=("Arial", 12, "bold"), 
                  bg="#27AE60", fg="white", height=2, command=self.save_and_exit).pack(side="left", fill="x", expand=True, padx=(0, 5))
        tk.Button(btn_container, text="關閉程式", font=("Arial", 12, "bold"), 
                  bg="#7F8C8D", fg="white", height=2, command=self.safe_close).pack(side="left", fill="x", expand=True, padx=(5, 0))

        # --- 新增：兩個功能按鈕並排 ---
        bottom_btn_frame = tk.Frame(self.root)
        bottom_btn_frame.pack(pady=10, padx=20, fill="x")
        
        tk.Button(bottom_btn_frame, text="歷史回報紀錄", font=("微軟正黑體", 14, "bold"), 
                  bg="#FFFF00", fg="#FF0000", bd=4, relief="ridge",
                  command=self.open_log_viewer).pack(side="left", fill="x", expand=True, padx=(0, 5))

        tk.Button(bottom_btn_frame, text="📊 異常數據統計", font=("微軟正黑體", 14, "bold"), 
                  bg="#E67E22", fg="white", bd=4, relief="ridge",
                  command=self.show_statistics).pack(side="left", fill="x", expand=True, padx=(5, 0))

    def safe_close(self):
        self.auto_backup_data()
        self.root.destroy()

    def show_statistics(self):
        """[新增功能] 異常數據自動統計報表"""
        log_path = os.path.join(self.base_path, 'work_logs.txt')
        if not os.path.exists(log_path):
            messagebox.showinfo("提示", "目前尚無回報紀錄，無法統計。")
            return
            
        issue_counts = []
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                content = f.read()
                records = content.split("="*45)
                for rec in records:
                    match = re.search(r"問題[:：]\s*(.*)", rec)
                    if match:
                        issue_counts.append(match.group(1).strip())
            
            if not issue_counts:
                messagebox.showinfo("提示", "未找到有效問題紀錄。")
                return

            # 統計排名
            stats = Counter(issue_counts).most_common(10) # 顯示前10名
            
            stat_win = tk.Toplevel(self.root)
            stat_win.title("異常數據分析報表")
            stat_win.geometry("500x450")
            stat_win.grab_set()

            tk.Label(stat_win, text="🔥 近期熱門異常排行榜", font=("Arial", 14, "bold"), pady=15).pack()
            
            # 使用列表顯示數據
            cols = ("rank", "issue", "count")
            tree = ttk.Treeview(stat_win, columns=cols, show="headings")
            tree.heading("rank", text="排名"); tree.column("rank", width=50, anchor="center")
            tree.heading("issue", text="異常問題名稱"); tree.column("issue", width=300)
            tree.heading("count", text="發生次時"); tree.column("count", width=100, anchor="center")
            tree.pack(padx=20, pady=10, fill="both", expand=True)

            for i, (issue, count) in enumerate(stats, 1):
                tree.insert("", "end", values=(f"第 {i} 名", issue, f"{count} 次"))

            tk.Button(stat_win, text="關閉報表", command=stat_win.destroy, bg="#2C3E50", fg="white", pady=5).pack(pady=10)
        except Exception as e:
            messagebox.showerror("統計失敗", f"讀取紀錄時出錯: {e}")

    def calculate_step_probabilities(self, issue_name, step_list):
        log_path = os.path.join(self.base_path, 'work_logs.txt')
        total_steps = len(step_list)
        if total_steps == 0: return {}
        initial_prob = round(100 / total_steps, 1)
        step_stats = {step: {"count": 0, "prob": initial_prob} for step in step_list}
        if not os.path.exists(log_path): return step_stats
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                content = f.read()
                records = content.split("="*45)
                target_records = [r for r in records if f"問題" in r and issue_name in r]
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

    def open_admin(self):
        admin_win = tk.Toplevel(self.root)
        admin_win.title("排除手法管理後台")
        admin_win.geometry("700x550")
        admin_win.grab_set() 
        self.editing_index = None
        list_frame = tk.LabelFrame(admin_win, text=" 現有異常清單 (點選開始編輯) ", padx=10, pady=10)
        list_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.issue_listbox = tk.Listbox(list_frame, font=("Arial", 11))
        self.issue_listbox.pack(fill="both", expand=True)
        edit_frame = tk.LabelFrame(admin_win, text=" 資料編輯區 ", padx=10, pady=10)
        edit_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        tk.Label(edit_frame, text="異常標題:").pack(anchor="w")
        ent_issue = tk.Entry(edit_frame, font=("Arial", 11)); ent_issue.pack(fill="x", pady=5)
        tk.Label(edit_frame, text="搜尋關鍵字:").pack(anchor="w")
        ent_kw = tk.Entry(edit_frame, font=("Arial", 11)); ent_kw.pack(fill="x", pady=5)
        tk.Label(edit_frame, text="排除步驟 (以分號 ; 分隔):").pack(anchor="w")
        txt_sol = tk.Text(edit_frame, height=12, font=("Arial", 11)); txt_sol.pack(fill="both", expand=True, pady=5)

        def refresh_lb():
            self.issue_listbox.delete(0, tk.END)
            for i, item in enumerate(self.handbook, 1): 
                self.issue_listbox.insert(tk.END, f"{i}. {item.get('issue', '無標題')}")

        def load_selected(event):
            selection = self.issue_listbox.curselection()
            if selection:
                idx = selection[0]
                if self.editing_index == idx: return 
                self.editing_index = idx
                data = self.handbook[idx]
                ent_issue.delete(0, tk.END); ent_issue.insert(0, data['issue'])
                ent_kw.delete(0, tk.END); ent_kw.insert(0, data['keyword'])
                raw_sol = str(data.get('solution', ''))
                steps = raw_sol.replace('；', ';').replace('\n', ';').split(';')
                formatted_sol = ""
                count = 1
                for s in steps:
                    txt = s.strip()
                    if txt:
                        txt = re.sub(r'^\d+[\.\s]*', '', txt) 
                        formatted_sol += f"{count}. {txt}\n"
                        count += 1
                txt_sol.delete("1.0", tk.END); txt_sol.insert("1.0", formatted_sol.strip())

        def clear_inputs():
            self.editing_index = None
            self.issue_listbox.selection_clear(0, tk.END)
            ent_issue.delete(0, tk.END); ent_kw.delete(0, tk.END); txt_sol.delete("1.0", tk.END)

        def save_modify():
            if self.editing_index is None: return
            new_data = {"keyword": ent_kw.get().strip(), "issue": ent_issue.get().strip(), "solution": txt_sol.get("1.0", tk.END).strip()}
            self.handbook[self.editing_index] = new_data
            if self.save_handbook(): refresh_lb(); messagebox.showinfo("成功", "資料修改已儲存")

        def add_new():
            new_data = {"keyword": ent_kw.get().strip(), "issue": ent_issue.get().strip(), "solution": txt_sol.get("1.0", tk.END).strip()}
            self.handbook.append(new_data)
            if self.save_handbook(): refresh_lb(); clear_inputs(); messagebox.showinfo("成功", "已新增新項目")

        def delete_item():
            if self.editing_index is None: return
            if messagebox.askyesno("確認", "確定要刪除嗎?"):
                self.handbook.pop(self.editing_index); self.save_handbook(); refresh_lb(); clear_inputs()

        self.issue_listbox.bind('<<ListboxSelect>>', load_selected)
        btn_f1 = tk.Frame(edit_frame); btn_f1.pack(fill="x", pady=5)
        tk.Button(btn_f1, text="儲存修改", command=save_modify, bg="#2980B9", fg="white", width=12).pack(side="left", padx=5)
        tk.Button(btn_f1, text="新增為新項目", command=add_new, bg="#27AE60", fg="white", width=12).pack(side="left", padx=5)
        btn_f2 = tk.Frame(edit_frame); btn_f2.pack(fill="x", pady=5)
        tk.Button(btn_f2, text="清空/取消", command=clear_inputs, bg="#F39C12", fg="white", width=12).pack(side="left", padx=5)
        tk.Button(btn_f2, text="刪除此項目", command=delete_item, bg="#C62828", fg="white", width=12).pack(side="left", padx=5)
        refresh_lb()

    def open_log_viewer(self):
        log_win = tk.Toplevel(self.root)
        log_win.title("立案紀錄查詢")
        log_win.geometry("900x500") 
        log_win.grab_set()
        columns = ("time", "user", "issue", "action")
        tree = ttk.Treeview(log_win, columns=columns, show="headings")
        tree.heading("time", text="時間"); tree.heading("user", text="人員")
        tree.heading("issue", text="異常問題"); tree.heading("action", text="回報經過")
        tree.column("time", width=140); tree.column("user", width=100)
        tree.column("issue", width=250); tree.column("action", width=350)
        tree.pack(padx=10, pady=10, fill="both", expand=True)
        detail_txt = tk.Text(log_win, height=8, bg="#F9F9F9", font=("Arial", 11))
        detail_txt.pack(padx=10, pady=(0, 10), fill="x")
        detail_txt.config(state="disabled")
        log_path = os.path.join(self.base_path, 'work_logs.txt')
        record_list = []
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8') as f:
                content = f.read()
                records = content.split("="*45)
                for rec in records:
                    rec = rec.strip()
                    if not rec: continue
                    try:
                        time = re.search(r"時間[:：]\s*(.*)", rec).group(1).strip()
                        user = re.search(r"人員[:：]\s*(.*)", rec).group(1).strip()
                        issue = re.search(r"問題[:：]\s*(.*)", rec).group(1).strip()
                        action = re.search(r"經過[:：]\s*(.*)", rec).group(1).strip()
                        iid = tree.insert("", "end", values=(time, user, issue, action))
                        record_list.append({"id": iid, "full": rec})
                    except: continue
                        
        def on_select(event):
            selected = tree.selection()
            if selected:
                for r in record_list:
                    if r["id"] == selected[0]:
                        detail_txt.config(state="normal"); detail_txt.delete("1.0", tk.END)
                        detail_txt.insert("1.0", r["full"]); detail_txt.config(state="disabled")
                        break
        tree.bind("<<TreeviewSelect>>", on_select)
        tk.Button(log_win, text="關閉視窗", command=log_win.destroy).pack(pady=5)

    def search_issue(self):
        query_str = self.query_entry.get().strip().lower()
        if not query_str: return
        search_terms = query_str.split()
        self.result_display.config(state="normal")
        self.result_display.delete("1.0", tk.END)
        found_item = None
        for item in self.handbook:
            target_text = (str(item.get('keyword', '')) + " " + str(item.get('issue', ''))).lower()
            if all(term in target_text for term in search_terms):
                found_item = item; break
        if found_item:
            self.found_item_ref = found_item 
            self.current_issue = found_item.get('issue', '未知問題')
            self.result_display.insert(tk.END, f"【問題描述】: {self.current_issue}\n", "bold")
            self.result_display.insert(tk.END, "-"*40 + "\n")
            raw_steps = str(found_item.get('solution', '')).replace('；', ';').replace('\n', ';').split(';')
            clean_steps = [re.sub(r'^\d+[\.\s]*', '', s.strip()) for s in raw_steps if s.strip()]
            stats = self.calculate_step_probabilities(self.current_issue, clean_steps)
            count = 1
            for txt in clean_steps:
                prob = stats[txt]["prob"]
                if prob >= 80: tag, status = "high", "[強烈推薦]"
                elif prob >= 50: tag, status = "mid", "[建議嘗試]"
                elif prob > 0: tag, status = "low", "[參考方案]" 
                else: tag, status = "new", "[可測試]" 
                self.result_display.insert(tk.END, f" {count}. {txt} ")
                self.result_display.insert(tk.END, f"({prob}%) {status}\n", tag)
                count += 1
        else:
            self.found_item_ref = None
            self.result_display.insert(tk.END, "❌ 找不到相關方案")
        self.result_display.config(state="disabled")

    def save_and_exit(self):
        action = self.action_entry.get().strip()
        if not action or not self.current_issue:
            messagebox.showwarning("提示", "請完成搜尋並填寫回報內容"); return
        if self.extra_fix_var.get() and self.found_item_ref:
            current_sol = self.found_item_ref.get('solution', '').strip()
            new_sol = current_sol + (";" if current_sol else "") + action
            self.found_item_ref['solution'] = new_sol
            self.save_handbook() 
        log_path = os.path.join(self.base_path, 'work_logs.txt')
        log = (f"● 時間：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
               f"● 人員：{self.current_user} ({self.current_uid})\n"
               f"● 問題：{self.current_issue}\n"
               f"● 經過：{action}\n" + "="*45 + "\n")
        try:
            with open(log_path, 'a', encoding='utf-8') as f: f.write(log)
            self.auto_backup_data()
            messagebox.showinfo("成功", "已完成立案！")
            self.query_entry.delete(0, tk.END); self.action_entry.delete(0, tk.END)
            self.extra_fix_var.set(False)
            self.result_display.config(state="normal")
            self.result_display.delete("1.0", tk.END)
            self.result_display.config(state="disabled")
            self.found_item_ref = None; self.current_issue = None
        except Exception as e: messagebox.showerror("錯誤", f"存檔失敗: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = GuardianApp(root)
    root.mainloop()
