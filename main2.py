import streamlit as st
import streamlit.components.v1 as components
import datetime
import math
import html
import pandas as pd
from firebase_admin import db

def _normalize_hex_color(color):
    color = str(color or "#1f77b4").strip()
    if not color.startswith("#"):
        color = "#" + color
    if len(color) == 4:
        color = "#" + "".join(ch * 2 for ch in color[1:])
    if len(color) != 7:
        return "#1f77b4"
    try:
        int(color[1:], 16)
        return color.lower()
    except ValueError:
        return "#1f77b4"


def _adjust_hex_color(color, factor):
    color = _normalize_hex_color(color)
    rgb = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
    if factor >= 1:
        out = [round(v + (255 - v) * min(factor - 1, 1)) for v in rgb]
    else:
        out = [round(v * max(factor, 0)) for v in rgb]
    return "#" + "".join(f"{max(0, min(255, v)):02x}" for v in out)


def _donut_sector_path(start_angle, end_angle, outer_radius, inner_radius):
    delta = end_angle - start_angle
    if delta >= (2 * math.pi - 1e-6):
        return (
            f"M {outer_radius:.3f} 0 "
            f"A {outer_radius:.3f} {outer_radius:.3f} 0 1 1 {-outer_radius:.3f} 0 "
            f"A {outer_radius:.3f} {outer_radius:.3f} 0 1 1 {outer_radius:.3f} 0 "
            f"L {inner_radius:.3f} 0 "
            f"A {inner_radius:.3f} {inner_radius:.3f} 0 1 0 {-inner_radius:.3f} 0 "
            f"A {inner_radius:.3f} {inner_radius:.3f} 0 1 0 {inner_radius:.3f} 0 Z"
        )

    x1 = outer_radius * math.cos(start_angle)
    y1 = outer_radius * math.sin(start_angle)
    x2 = outer_radius * math.cos(end_angle)
    y2 = outer_radius * math.sin(end_angle)
    x3 = inner_radius * math.cos(end_angle)
    y3 = inner_radius * math.sin(end_angle)
    x4 = inner_radius * math.cos(start_angle)
    y4 = inner_radius * math.sin(start_angle)
    large_arc = 1 if delta > math.pi else 0
    return (
        f"M {x1:.3f} {y1:.3f} "
        f"A {outer_radius:.3f} {outer_radius:.3f} 0 {large_arc} 1 {x2:.3f} {y2:.3f} "
        f"L {x3:.3f} {y3:.3f} "
        f"A {inner_radius:.3f} {inner_radius:.3f} 0 {large_arc} 0 {x4:.3f} {y4:.3f} Z"
    )


def _spread_label_positions(items, min_y, max_y, gap):
    if not items:
        return items
    items = sorted(items, key=lambda x: x["target_y"])
    items[0]["label_y"] = max(min_y, items[0]["target_y"])
    for i in range(1, len(items)):
        items[i]["label_y"] = max(items[i]["target_y"], items[i - 1]["label_y"] + gap)
    overflow = items[-1]["label_y"] - max_y
    if overflow > 0:
        for item in items:
            item["label_y"] -= overflow
    underflow = min_y - items[0]["label_y"]
    if underflow > 0:
        for item in items:
            item["label_y"] += underflow
    return items


def _build_3d_donut_html(chart_df, total_cnt):
    width, height = 720, 450
    cx, cy = 360, 205
    outer_radius, inner_radius = 142, 76
    flatten = 0.72
    start_angle = -math.pi / 2
    sectors = []

    for _, row in chart_df.iterrows():
        cnt = int(row["件數"])
        pct = float(row["百分比"])
        angle = (cnt / total_cnt) * 2 * math.pi if total_cnt else 0
        end_angle = start_angle + angle
        color = _normalize_hex_color(row["顏色"])
        sectors.append({
            "category": str(row["分類"]),
            "count": cnt,
            "pct": pct,
            "color": color,
            "mid": start_angle + angle / 2,
            "path": _donut_sector_path(start_angle, end_angle, outer_radius, inner_radius),
        })
        start_angle = end_angle

    gradients = []
    for i, sec in enumerate(sectors):
        light = _adjust_hex_color(sec["color"], 1.35)
        dark = _adjust_hex_color(sec["color"], 0.72)
        gradients.append(
            f'<linearGradient id="g{i}" x1="0%" y1="0%" x2="100%" y2="100%">'
            f'<stop offset="0%" stop-color="{light}"/><stop offset="52%" stop-color="{sec["color"]}"/>'
            f'<stop offset="100%" stop-color="{dark}"/></linearGradient>'
        )

    depth_paths = []
    for depth in range(18, 1, -2):
        opacity = 0.25 + (18 - depth) * 0.012
        for sec in sectors:
            depth_color = _adjust_hex_color(sec["color"], 0.44)
            depth_paths.append(
                f'<path d="{sec["path"]}" fill="{depth_color}" opacity="{opacity:.2f}" '
                f'transform="translate({cx},{cy + depth}) scale(1,{flatten})"/>'
            )

    top_paths = []
    for i, sec in enumerate(sectors):
        cat = html.escape(sec["category"])
        top_paths.append(
            f'<path d="{sec["path"]}" fill="url(#g{i})" stroke="rgba(255,255,255,0.72)" stroke-width="1.4" '
            f'transform="translate({cx},{cy}) scale(1,{flatten})" filter="url(#glow)">'
            f'<title>{cat}：{sec["count"]} 件（{sec["pct"]:.1f}%）</title></path>'
        )

    labels_left, labels_right = [], []
    for sec in sectors:
        mid = sec["mid"]
        side = "right" if math.cos(mid) >= 0 else "left"
        edge_x = cx + math.cos(mid) * (outer_radius + 3)
        edge_y = cy + math.sin(mid) * (outer_radius + 3) * flatten
        bend_x = cx + math.cos(mid) * (outer_radius + 28)
        bend_y = cy + math.sin(mid) * (outer_radius + 28) * flatten
        item = {
            "sec": sec,
            "edge_x": edge_x,
            "edge_y": edge_y,
            "bend_x": bend_x,
            "bend_y": bend_y,
            "target_y": bend_y,
        }
        (labels_right if side == "right" else labels_left).append(item)

    labels_left = _spread_label_positions(labels_left, 82, 348, 34)
    labels_right = _spread_label_positions(labels_right, 82, 348, 34)

    label_svg = []
    for side, items in (("left", labels_left), ("right", labels_right)):
        for item in items:
            sec = item["sec"]
            label_y = item["label_y"]
            if side == "right":
                line_end_x, text_x, anchor = 555, 566, "start"
            else:
                line_end_x, text_x, anchor = 165, 154, "end"
            label_svg.append(
                f'<polyline points="{item["edge_x"]:.1f},{item["edge_y"]:.1f} '
                f'{item["bend_x"]:.1f},{item["bend_y"]:.1f} {line_end_x},{label_y:.1f}" '
                f'fill="none" stroke="{sec["color"]}" stroke-width="1.8" opacity="0.95"/>'
                f'<circle cx="{line_end_x}" cy="{label_y:.1f}" r="3.4" fill="{sec["color"]}" filter="url(#dotGlow)"/>'
                f'<text x="{text_x}" y="{label_y - 4:.1f}" text-anchor="{anchor}" class="label-title">'
                f'{html.escape(sec["category"])}</text>'
                f'<text x="{text_x}" y="{label_y + 14:.1f}" text-anchor="{anchor}" class="label-pct">'
                f'{sec["pct"]:.1f}% · {sec["count"]} 件</text>'
            )

    return f"""
    <div class="bi-chart-shell">
      <div class="scanline"></div>
      <div class="chart-title">品質異常分類｜3D 智慧分佈</div>
      <div class="chart-subtitle">QUALITY ANOMALY INTELLIGENCE</div>
      <svg viewBox="0 0 {width} {height}" width="100%" height="100%" role="img" aria-label="品質異常分類立體圓環圖">
        <defs>
          {''.join(gradients)}
          <filter id="glow" x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="2.2" result="blur"/>
            <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
          <filter id="dotGlow" x="-200%" y="-200%" width="500%" height="500%">
            <feGaussianBlur stdDeviation="2.6" result="blur"/>
            <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
          <radialGradient id="coreGlow">
            <stop offset="0%" stop-color="#0d3855" stop-opacity="0.94"/>
            <stop offset="72%" stop-color="#061723" stop-opacity="0.97"/>
            <stop offset="100%" stop-color="#02070d"/>
          </radialGradient>
        </defs>
        <ellipse cx="{cx}" cy="{cy + 116}" rx="158" ry="26" fill="#000" opacity="0.34" filter="url(#glow)"/>
        {''.join(depth_paths)}
        {''.join(top_paths)}
        <ellipse cx="{cx}" cy="{cy}" rx="{inner_radius - 3}" ry="{(inner_radius - 3) * flatten:.1f}" fill="url(#coreGlow)" stroke="#40e0ff" stroke-opacity="0.42" stroke-width="1.4"/>
        <text x="{cx}" y="{cy - 6}" text-anchor="middle" class="center-kicker">異常總數</text>
        <text x="{cx}" y="{cy + 22}" text-anchor="middle" class="center-value">{int(total_cnt)}</text>
        <text x="{cx}" y="{cy + 43}" text-anchor="middle" class="center-unit">件</text>
        {''.join(label_svg)}
      </svg>
    </div>
    <style>
      html, body {{ margin:0; padding:0; background:transparent; overflow:hidden; }}
      .bi-chart-shell {{
        position:relative; height:438px; border-radius:24px; overflow:hidden;
        background:
          radial-gradient(circle at 50% 42%, rgba(20,112,150,.28), transparent 34%),
          linear-gradient(145deg, rgba(7,25,39,.98), rgba(2,8,15,.99));
        border:1px solid rgba(95,223,255,.28);
        box-shadow: inset 0 0 45px rgba(31,196,255,.07), 0 18px 45px rgba(1,8,15,.32);
        font-family: "Microsoft JhengHei", "Noto Sans TC", sans-serif;
      }}
      .bi-chart-shell:before {{
        content:""; position:absolute; inset:0; pointer-events:none;
        background-image: linear-gradient(rgba(84,220,255,.04) 1px, transparent 1px), linear-gradient(90deg, rgba(84,220,255,.04) 1px, transparent 1px);
        background-size:28px 28px; mask-image:linear-gradient(to bottom, rgba(0,0,0,.75), transparent 92%);
      }}
      .scanline {{ position:absolute; left:0; right:0; height:2px; top:15%; background:linear-gradient(90deg,transparent,#4fe9ff,transparent); opacity:.22; animation:scan 5s linear infinite; }}
      @keyframes scan {{ 0%{{top:15%}} 100%{{top:92%}} }}
      .chart-title {{ position:absolute; top:18px; left:24px; color:#d9f8ff; font-weight:800; font-size:18px; letter-spacing:.8px; }}
      .chart-subtitle {{ position:absolute; top:44px; left:24px; color:#5ee7ff; opacity:.66; font-size:10px; letter-spacing:2.2px; }}
      svg {{ position:absolute; inset:28px 0 0 0; }}
      .label-title {{ fill:#e9fbff; font-size:14px; font-weight:800; paint-order:stroke; stroke:#051018; stroke-width:4px; }}
      .label-pct {{ fill:#77e9ff; font-size:13px; font-weight:800; paint-order:stroke; stroke:#051018; stroke-width:4px; }}
      .center-kicker {{ fill:#8cecff; font-size:13px; font-weight:700; letter-spacing:1px; }}
      .center-value {{ fill:#ffffff; font-size:32px; font-weight:900; filter:url(#glow); }}
      .center-unit {{ fill:#71dff5; font-size:12px; font-weight:700; }}
    </style>
    """


def render_page(current_menu):
    st.markdown("""
        <style>
        .stApp {
            background: linear-gradient(180deg, #fce4ec 0%, #f8bbd0 50%, #f48fb1 100%) !important;
            background-attachment: fixed;
        }
        .quality-header {
            background: linear-gradient(135deg, #ec407a, #d81b60);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.15);
            border: 1px solid #ff80ab;
        }
        .quality-header h2 {
            color: #0b192c !important;
        }
        .quality-card {
            background-color: #fce4ec;
            border-left: 6px solid #e91e63;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border: 1px solid #f8bbd0;
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
            border: 1px solid #e91e63 !important;
        }
        .stTextInput input, .stTextArea textarea {
            background-color: #ffffff !important;
            color: #0b192c !important;
        }
        section[data-testid="stSidebar"] .stButton>button,
        .stButton>button {
            width: 100%;
            background-color: #f06292 !important;
            border: 1px solid #ad1457 !important;
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
            background-color: #ec407a !important;
            border: 1px solid #f48fb1 !important;
        }

        .bi-kpi-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
            margin: 12px 0 18px 0;
        }
        .bi-kpi {
            position: relative;
            overflow: hidden;
            background: linear-gradient(145deg, rgba(5,24,38,0.98), rgba(8,43,61,0.95));
            border: 1px solid rgba(75,224,255,0.35);
            border-radius: 16px;
            padding: 14px 16px;
            box-shadow: 0 10px 28px rgba(0,28,43,0.22), inset 0 0 22px rgba(58,210,255,0.05);
        }
        .bi-kpi::after {
            content: "";
            position: absolute;
            left: 0; top: 0; bottom: 0; width: 3px;
            background: linear-gradient(180deg, #65efff, #008cff);
            box-shadow: 0 0 12px #38d9ff;
        }
        .bi-kpi-label { color: #8eeeff !important; font-size: 12px; letter-spacing: 1px; margin-bottom: 5px; }
        .bi-kpi-value { color: #ffffff !important; font-size: 25px; line-height: 1.1; font-weight: 900; }
        .bi-kpi-sub { color: #a9cbd4 !important; font-size: 11px; margin-top: 6px; }
        .bi-rank-row {
            background: linear-gradient(90deg, rgba(4,22,34,.96), rgba(10,48,64,.90));
            border: 1px solid rgba(80,220,255,.20);
            border-radius: 13px;
            padding: 10px 12px;
            margin: 0 0 10px 0;
            box-shadow: inset 0 0 18px rgba(56,212,255,.035);
        }
        .bi-rank-head { display:flex; justify-content:space-between; gap:12px; align-items:center; margin-bottom:7px; }
        .bi-rank-name { color:#e7fbff !important; font-weight:800; font-size:14px; }
        .bi-rank-pct { color:#75e8ff !important; font-weight:900; font-size:14px; }
        .bi-track { height:10px; border-radius:999px; background:rgba(255,255,255,.08); overflow:hidden; border:1px solid rgba(255,255,255,.05); }
        .bi-fill { height:100%; border-radius:999px; box-shadow:0 0 14px currentColor; }
        .bi-rank-meta { color:#a7c7d1 !important; font-size:11px; margin-top:6px; }
        @media (max-width: 900px) { .bi-kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
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

    def load_category_colors(cats):
        ref = db.reference('quality_category_colors')
        colors = ref.get()
        default_palette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        if not colors:
            colors = {}
        
        updated = False
        for i, cat in enumerate(cats):
            if cat not in colors:
                colors[cat] = default_palette[i % len(default_palette)]
                updated = True
        if updated:
            ref.set(colors)
        return colors

    def save_category_colors(colors):
        db.reference('quality_category_colors').set(colors)

    categories = load_categories()
    cat_colors = load_category_colors(categories)

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
                                    db.reference('quality_records').set(records)
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
                                    db.reference('quality_records').set(records)
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
                db.reference('quality_records').set(records)
                
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
                <h2>08. 異常分類百分比分佈</h2>
            </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="quality-card">', unsafe_allow_html=True)
        
        with st.expander("🎨 點擊展開：異常分類顏色自定義設定"):
            with st.form("color_config_form"):
                cols_color = st.columns(min(len(categories), 4))
                new_colors = cat_colors.copy()
                for idx, cat in enumerate(categories):
                    col_idx = idx % len(cols_color)
                    with cols_color[col_idx]:
                        curr_col = cat_colors.get(cat, "#1f77b4")
                        new_colors[cat] = st.color_picker(f"{cat}", value=curr_col, key=f"picker_{cat}")
                
                submitted_colors = st.form_submit_button("🔄 更新圖表顏色", use_container_width=True)
                if submitted_colors:
                    save_category_colors(new_colors)
                    cat_colors = new_colors
                    st.success("🎨 圖表顏色已更新！")

        st.markdown("---")
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
            total_cnt = len(filtered_recs)
            cat_counts = df['category'].value_counts()
            
            chart_data = []
            domain_colors = []
            range_colors = []
            for cat, cnt in cat_counts.items():
                pct = round((cnt / total_cnt) * 100, 1)
                c_color = cat_colors.get(cat, '#1f77b4')
                chart_data.append({
                    '分類': cat,
                    '件數': cnt,
                    '百分比': pct,
                    '顏色': c_color
                })
                domain_colors.append(cat)
                range_colors.append(c_color)

            chart_df = pd.DataFrame(chart_data)

            st.markdown("---")

            top_row = chart_df.sort_values(["件數", "百分比"], ascending=False).iloc[0]
            top_category = html.escape(str(top_row["分類"]))
            top_pct = float(top_row["百分比"])
            avg_per_category = round(total_cnt / max(len(chart_df), 1), 1)
            st.markdown(
                f"""
                <div class="bi-kpi-grid">
                    <div class="bi-kpi">
                        <div class="bi-kpi-label">異常總數</div>
                        <div class="bi-kpi-value">{total_cnt} 件</div>
                        <div class="bi-kpi-sub">所選日期區間累計</div>
                    </div>
                    <div class="bi-kpi">
                        <div class="bi-kpi-label">異常分類數</div>
                        <div class="bi-kpi-value">{len(chart_df)} 類</div>
                        <div class="bi-kpi-sub">實際有發生紀錄的分類</div>
                    </div>
                    <div class="bi-kpi">
                        <div class="bi-kpi-label">最高異常分類</div>
                        <div class="bi-kpi-value" style="font-size:20px;">{top_category}</div>
                        <div class="bi-kpi-sub">佔全部異常 {top_pct:.1f}%</div>
                    </div>
                    <div class="bi-kpi">
                        <div class="bi-kpi-label">平均分類件數</div>
                        <div class="bi-kpi-value">{avg_per_category}</div>
                        <div class="bi-kpi-sub">每一有效分類平均件數</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            col_chart, col_bars = st.columns([1.5, 1])

            with col_chart:
                # 自製 SVG 立體圓環：百分比/件數使用外側引線標註，避免文字壓在圖形上。
                chart_html = _build_3d_donut_html(chart_df, total_cnt)
                components.html(chart_html, height=455, scrolling=False)

            with col_bars:
                st.markdown("### 📊 分類佔比排行")
                for _, row in chart_df.sort_values("百分比", ascending=False).iterrows():
                    cat_name = html.escape(str(row["分類"]))
                    pct_val = float(row["百分比"])
                    cnt_val = int(row["件數"])
                    bar_color = _normalize_hex_color(row["顏色"])
                    bar_light = _adjust_hex_color(bar_color, 1.35)
                    st.markdown(
                        f"""
                        <div class="bi-rank-row">
                            <div class="bi-rank-head">
                                <div class="bi-rank-name">{cat_name}</div>
                                <div class="bi-rank-pct">{pct_val:.1f}%</div>
                            </div>
                            <div class="bi-track">
                                <div class="bi-fill" style="width:{max(0, min(100, pct_val))}%; color:{bar_color}; background:linear-gradient(90deg,{bar_color},{bar_light});"></div>
                            </div>
                            <div class="bi-rank-meta">異常件數：{cnt_val} 件</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            st.markdown("---")
            summary_str = " · ".join([f"{row['分類']} {row['件數']} 件 ({row['百分比']}%)" for index, row in chart_df.iterrows()])
            st.markdown(f"**統計摘要：** {summary_str}")

            st.markdown("---")
            st.markdown("### 1. 明細（符合條件的詳細異常紀錄）")
            chinese_columns = {
                "order": "製令",
                "date": "建立日期",
                "category": "異常分類",
                "content": "異常內容",
                "solution": "排除方式",
                "countermeasure": "對策",
                "status": "追蹤狀況",
                "person": "異常人員",
            }
            detail_df = df.reindex(columns=list(chinese_columns.keys())).rename(columns=chinese_columns)
            st.dataframe(detail_df, use_container_width=True, hide_index=True)
            
        else:
            st.info("ℹ️ 於所選的日期區間內尚無品質異常紀錄資料。")
            
        st.markdown('</div>', unsafe_allow_html=True)
