#!/usr/bin/env python3
"""
美股機構日報自動生成腳本
每天由 GitHub Actions 自動執行，呼叫 Claude API 生成日報並更新網頁
"""

import anthropic
import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── 台灣時間 ──────────────────────────────────────────────────
TZ_TAIPEI = timezone(timedelta(hours=8))
now_tw = datetime.now(TZ_TAIPEI)
date_str = now_tw.strftime("%Y/%m/%d")
date_file = now_tw.strftime("%Y-%m-%d")
weekday_map = ["週一","週二","週三","週四","週五","週六","週日"]
weekday_str = weekday_map[now_tw.weekday()]

print(f"[{datetime.now()}] 開始生成 {date_str} 美股日報...")

# ── Claude API 呼叫 ───────────────────────────────────────────
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

PROMPT = f"""請幫我生成今日【美股機構日報】，日期：{date_str}（{weekday_str}）。

你必須使用 Bigdata.com MCP 工具自動抓取以下即時數據：
1. bigdata_market_tearsheet - 全市場快照（VIX、美債、板塊、商品、匯率）
2. bigdata_country_tearsheet(country="US") - 美國宏觀數據（GDP、CPI、Fed）
3. 個股數據（TSLA、CRCL、CRWD、GOOGL、SMH、TSM、VRT、VST、IREN）

請生成一份完整的繁體中文日報，包含以下所有章節：

## 一、宏觀水位監控
- US10Y、VIX、WTI原油、黃金、BTC、EUR/USD、USD/TWD
- 完整表格含1日/5日/1月變動
- 宏觀總結一段（3-5句，點出最重要的市場驅動力）

## 二、全球市場快照
- 亞太主要市場表現（台灣/韓國/日本/中國/印度）
- 美股板塊本週勝負表（全11個板塊，含YTD）
- 因子輪動分析（動能/成長/價值/小型股/低波動）

## 三、核心持倉快照
所有標的必須包含：收盤價、1日漲跌、5日漲跌、RS評分(vs QQQ)、52週區間位置、趨勢判斷、狀態摘要
標的：TSLA、CRCL、CRWD、GOOGL、SMH、TSM、VRT、VST、IREN

## 四、個股深度掃描（每支至少4個bullet）
重點分析：TSM、VRT、TSLA、CRCL、CRWD
每支包含：基本面數據、機構動態（分析師評級/目標價）、技術點位（支撐/壓力）、期權結構、操作建議與信心評分

## 五、財報日曆（未來30天）
列出所有核心持倉的財報日期、預期EPS、前一季超預期幅度

## 六、社群謠言粉碎機（3-5則）
格式：傳聞 → 判定（✅確認/⚠️過度解讀/❌錯誤）→ 華爾街點評

## 七、操盤手指令
完整表格：標的、建議(買入/觀望/避開)、信心(★)、進場價、目標價、止損、核心理由

## 八、本週總結
三個最重要的事件/數據，下週最大看點，整體市場定調（一句話）

格式要求：
- 繁體中文
- 數字精確（來自真實數據）
- 每個章節都要有豐富的表格和分析
- 語氣專業犀利，像頂級賣方分析師
- 結尾加上免責聲明"""

print("呼叫 Claude API（含 Bigdata.com MCP）...")

try:
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        mcp_servers=[
            {
                "type": "url",
                "url": "https://mcp.bigdata.com",
                "name": "bigdata"
            }
        ],
        messages=[{"role": "user", "content": PROMPT}]
    )
    
    # 提取文字內容
    report_content = ""
    for block in message.content:
        if block.type == "text":
            report_content += block.text
    
    print(f"✅ 日報生成成功，共 {len(report_content)} 字元")

except Exception as e:
    print(f"❌ API 呼叫失敗：{e}")
    # 若 MCP 不可用，退回純文字模式
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=6000,
        messages=[{
            "role": "user", 
            "content": f"請用你最新的知識生成 {date_str} 的美股市場分析日報（繁體中文），包含宏觀、板塊、個股（TSLA/TSM/VRT/CRWD/CRCL/GOOGL/SMH/VST/IREN）、操盤建議等完整章節。請標注這是基於訓練數據的分析，非即時數據。"
        }]
    )
    report_content = message.content[0].text
    print(f"⚠️ 使用備用模式，共 {len(report_content)} 字元")

# ── 將 Markdown 轉換為 HTML ───────────────────────────────────
def md_to_html(text):
    """簡單的 Markdown → HTML 轉換"""
    lines = text.split('\n')
    html_parts = []
    in_table = False
    in_code = False
    
    for line in lines:
        # 程式碼區塊
        if line.strip().startswith('```'):
            if in_code:
                html_parts.append('</code></pre>')
                in_code = False
            else:
                html_parts.append('<pre><code>')
                in_code = True
            continue
        if in_code:
            html_parts.append(line.replace('<','&lt;').replace('>','&gt;'))
            continue
        
        # 表格
        if '|' in line and line.strip().startswith('|'):
            if not in_table:
                html_parts.append('<div class="table-wrap"><table>')
                in_table = True
            cells = [c.strip() for c in line.split('|')[1:-1]]
            # 分隔行
            if all(set(c.replace('-','').replace(':','').strip()) == set() or c.strip().replace('-','').replace(':','') == '' for c in cells):
                continue
            # 判斷是否標題行（前一行是否為表格開始）
            is_header = html_parts[-1] == '<div class="table-wrap"><table>' or \
                        (len(html_parts) >= 2 and html_parts[-2] == '<div class="table-wrap"><table>')
            tag = 'th' if is_header else 'td'
            row_html = '<tr>' + ''.join(f'<{tag}>{c}</{tag}>' for c in cells) + '</tr>'
            html_parts.append(row_html)
            continue
        else:
            if in_table:
                html_parts.append('</table></div>')
                in_table = False
        
        # 標題
        if line.startswith('# '):
            html_parts.append(f'<h1>{line[2:]}</h1>')
        elif line.startswith('## '):
            html_parts.append(f'<h2>{line[3:]}</h2>')
        elif line.startswith('### '):
            html_parts.append(f'<h3>{line[4:]}</h3>')
        elif line.startswith('#### '):
            html_parts.append(f'<h4>{line[5:]}</h4>')
        # 清單
        elif line.startswith('- ') or line.startswith('• '):
            html_parts.append(f'<li>{line[2:]}</li>')
        elif re.match(r'^\d+\. ', line):
            content = re.sub(r'^\d+\. ', '', line)
            html_parts.append(f'<li class="num">{content}</li>')
        # 引用
        elif line.startswith('> '):
            html_parts.append(f'<blockquote>{line[2:]}</blockquote>')
        # 分隔線
        elif line.strip() in ('---', '***', '___'):
            html_parts.append('<hr>')
        # 空行
        elif line.strip() == '':
            html_parts.append('<br>')
        # 一般段落
        else:
            # 粗體/斜體
            line = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
            line = re.sub(r'\*(.+?)\*', r'<em>\1</em>', line)
            line = re.sub(r'`(.+?)`', r'<code>\1</code>', line)
            html_parts.append(f'<p>{line}</p>')
    
    if in_table:
        html_parts.append('</table></div>')
    
    return '\n'.join(html_parts)

report_html = md_to_html(report_content)

# ── 載入歷史日報（最近30天）─────────────────────────────────
history_file = Path("history.json")
if history_file.exists():
    with open(history_file, "r", encoding="utf-8") as f:
        history = json.load(f)
else:
    history = []

# 加入今日日報
history.insert(0, {
    "date": date_str,
    "date_file": date_file,
    "weekday": weekday_str,
    "content": report_content  # 儲存原始 Markdown
})

# 只保留最近30天
history = history[:30]

with open(history_file, "w", encoding="utf-8") as f:
    json.dump(history, f, ensure_ascii=False, indent=2)

# ── 生成完整 HTML 頁面 ────────────────────────────────────────
html_template = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="3600">
<title>🇺🇸 美股機構日報 {date_str}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500;700;900&family=JetBrains+Mono:wght@400;600&family=Bebas+Neue&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #0a0e1a;
    --bg2: #0f1629;
    --bg3: #141d35;
    --card: #161e36;
    --card2: #1a2540;
    --border: #1e2d4a;
    --accent: #e94560;
    --accent2: #ff6b8a;
    --blue: #3b82f6;
    --blue2: #60a5fa;
    --green: #10b981;
    --red: #ef4444;
    --orange: #f59e0b;
    --purple: #8b5cf6;
    --text: #e2e8f0;
    --text2: #94a3b8;
    --text3: #64748b;
    --gold: #fbbf24;
  }}

  * {{ margin:0; padding:0; box-sizing:border-box; }}

  body {{
    background: var(--bg);
    color: var(--text);
    font-family: 'Noto Sans TC', sans-serif;
    font-size: 14px;
    line-height: 1.7;
    min-height: 100vh;
  }}

  /* ── 背景網格紋理 ── */
  body::before {{
    content:'';
    position: fixed;
    inset: 0;
    background-image:
      linear-gradient(rgba(59,130,246,0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(59,130,246,0.03) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
    z-index: 0;
  }}

  /* ── Header ── */
  .site-header {{
    background: linear-gradient(135deg, #0a0e1a 0%, #0f1629 50%, #141028 100%);
    border-bottom: 1px solid var(--border);
    padding: 0;
    position: sticky;
    top: 0;
    z-index: 100;
    backdrop-filter: blur(20px);
  }}

  .header-top {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 32px;
    border-bottom: 1px solid rgba(255,255,255,0.05);
  }}

  .logo {{
    font-family: 'Bebas Neue', sans-serif;
    font-size: 22px;
    letter-spacing: 3px;
    color: var(--text);
    display: flex;
    align-items: center;
    gap: 10px;
  }}

  .logo-dot {{ width:8px; height:8px; border-radius:50%; background:var(--accent); animation: pulse 2s infinite; }}
  @keyframes pulse {{ 0%,100% {{ opacity:1; transform:scale(1); }} 50% {{ opacity:0.5; transform:scale(1.3); }} }}

  .header-meta {{
    display: flex;
    gap: 20px;
    align-items: center;
    font-size: 12px;
    color: var(--text3);
    font-family: 'JetBrains Mono', monospace;
  }}

  .live-badge {{
    background: rgba(16,185,129,0.15);
    border: 1px solid var(--green);
    color: var(--green);
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
  }}

  /* ── 日期選擇器 ── */
  .date-nav {{
    display: flex;
    gap: 8px;
    padding: 10px 32px;
    overflow-x: auto;
    scrollbar-width: none;
  }}
  .date-nav::-webkit-scrollbar {{ display:none; }}

  .date-btn {{
    background: var(--bg3);
    border: 1px solid var(--border);
    color: var(--text2);
    padding: 6px 16px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 12px;
    font-family: 'JetBrains Mono', monospace;
    white-space: nowrap;
    transition: all 0.2s;
  }}
  .date-btn:hover {{ border-color: var(--blue); color: var(--blue2); }}
  .date-btn.active {{
    background: var(--accent);
    border-color: var(--accent);
    color: white;
    font-weight: 700;
  }}

  /* ── 主容器 ── */
  .container {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 32px 24px;
    position: relative;
    z-index: 1;
  }}

  /* ── 報告標題 ── */
  .report-hero {{
    background: linear-gradient(135deg, var(--card) 0%, var(--card2) 100%);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 32px 40px;
    margin-bottom: 32px;
    position: relative;
    overflow: hidden;
  }}

  .report-hero::before {{
    content: '日報';
    position: absolute;
    right: -10px;
    top: -20px;
    font-family: 'Bebas Neue', sans-serif;
    font-size: 140px;
    color: rgba(255,255,255,0.02);
    pointer-events: none;
    letter-spacing: -5px;
  }}

  .report-hero h1 {{
    font-family: 'Bebas Neue', sans-serif;
    font-size: 42px;
    letter-spacing: 4px;
    color: white;
    margin-bottom: 8px;
    border: none;
    padding: 0;
    background: none;
  }}

  .report-hero .subtitle {{
    color: var(--text2);
    font-size: 13px;
    font-family: 'JetBrains Mono', monospace;
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
  }}

  .report-hero .subtitle span {{
    display: flex;
    align-items: center;
    gap: 6px;
  }}

  .accent-line {{
    width: 60px;
    height: 3px;
    background: linear-gradient(90deg, var(--accent), var(--purple));
    border-radius: 2px;
    margin: 12px 0;
  }}

  /* ── 報告內容樣式 ── */
  .report-body {{ line-height: 1.8; }}

  .report-body h1 {{
    font-family: 'Bebas Neue', sans-serif;
    font-size: 28px;
    letter-spacing: 3px;
    color: white;
    background: linear-gradient(135deg, var(--card2), var(--bg3));
    border: 1px solid var(--border);
    border-left: 4px solid var(--accent);
    padding: 16px 24px;
    border-radius: 8px;
    margin: 40px 0 20px;
  }}

  .report-body h2 {{
    font-size: 18px;
    font-weight: 700;
    color: var(--blue2);
    border-bottom: 1px solid var(--border);
    padding-bottom: 10px;
    margin: 32px 0 16px;
  }}

  .report-body h3 {{
    font-size: 15px;
    font-weight: 700;
    color: var(--gold);
    margin: 24px 0 12px;
    display: flex;
    align-items: center;
    gap: 8px;
  }}

  .report-body h4 {{
    font-size: 14px;
    font-weight: 600;
    color: var(--text2);
    margin: 16px 0 8px;
  }}

  .report-body p {{
    color: var(--text2);
    margin: 8px 0;
    line-height: 1.8;
  }}

  .report-body strong {{ color: var(--text); font-weight: 700; }}
  .report-body em {{ color: var(--accent2); font-style: normal; }}
  .report-body code {{
    background: rgba(59,130,246,0.1);
    border: 1px solid rgba(59,130,246,0.2);
    color: var(--blue2);
    padding: 1px 6px;
    border-radius: 4px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
  }}

  .report-body pre {{
    background: #0d1117;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px;
    overflow-x: auto;
    margin: 16px 0;
  }}
  .report-body pre code {{
    background: none;
    border: none;
    color: #e6edf3;
    font-size: 13px;
  }}

  .report-body blockquote {{
    background: rgba(59,130,246,0.08);
    border-left: 3px solid var(--blue);
    padding: 12px 20px;
    border-radius: 0 8px 8px 0;
    color: var(--text2);
    margin: 12px 0;
    font-style: italic;
  }}

  .report-body hr {{
    border: none;
    border-top: 1px solid var(--border);
    margin: 32px 0;
  }}

  .report-body li {{
    color: var(--text2);
    padding: 3px 0 3px 20px;
    position: relative;
  }}
  .report-body li::before {{
    content: '▸';
    position: absolute;
    left: 0;
    color: var(--accent);
  }}
  .report-body li.num::before {{
    content: none;
  }}

  /* ── 表格 ── */
  .table-wrap {{
    overflow-x: auto;
    margin: 16px 0;
    border-radius: 10px;
    border: 1px solid var(--border);
  }}

  .report-body table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }}

  .report-body th {{
    background: var(--bg3);
    color: var(--text);
    font-weight: 700;
    padding: 10px 14px;
    text-align: left;
    border-bottom: 2px solid var(--accent);
    white-space: nowrap;
    font-size: 12px;
    letter-spacing: 0.5px;
  }}

  .report-body td {{
    padding: 9px 14px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    color: var(--text2);
    vertical-align: top;
  }}

  .report-body tr:nth-child(even) td {{ background: rgba(255,255,255,0.02); }}
  .report-body tr:hover td {{ background: rgba(59,130,246,0.05); }}

  /* ── 側邊歷史列表 ── */
  .layout {{ display: flex; gap: 24px; align-items: flex-start; }}
  .main-content {{ flex: 1; min-width: 0; }}
  .sidebar {{
    width: 200px;
    flex-shrink: 0;
    position: sticky;
    top: 120px;
  }}

  .sidebar-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
  }}

  .sidebar-title {{
    font-size: 11px;
    font-weight: 700;
    color: var(--text3);
    letter-spacing: 2px;
    margin-bottom: 12px;
    text-transform: uppercase;
  }}

  .history-item {{
    display: block;
    padding: 8px 10px;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.2s;
    margin-bottom: 4px;
    border: 1px solid transparent;
  }}
  .history-item:hover {{ background: var(--bg3); border-color: var(--border); }}
  .history-item.active {{ background: rgba(233,69,96,0.1); border-color: var(--accent); }}
  .history-date {{ font-size: 12px; font-weight: 700; font-family: 'JetBrains Mono', monospace; color: var(--text); }}
  .history-day {{ font-size: 11px; color: var(--text3); }}

  /* ── 頁尾 ── */
  .footer {{
    text-align: center;
    padding: 40px 24px;
    color: var(--text3);
    font-size: 12px;
    border-top: 1px solid var(--border);
    margin-top: 48px;
  }}

  /* ── RWD ── */
  @media (max-width: 768px) {{
    .layout {{ flex-direction: column; }}
    .sidebar {{ width: 100%; position: static; }}
    .report-hero {{ padding: 24px 20px; }}
    .report-hero h1 {{ font-size: 30px; }}
    .container {{ padding: 16px; }}
    .header-top {{ padding: 12px 16px; }}
    .date-nav {{ padding: 10px 16px; }}
  }}

  /* ── 載入動畫 ── */
  .fade-in {{ animation: fadeIn 0.5s ease forwards; }}
  @keyframes fadeIn {{ from {{ opacity:0; transform:translateY(8px); }} to {{ opacity:1; transform:translateY(0); }} }}
</style>
</head>
<body>

<!-- Header -->
<header class="site-header">
  <div class="header-top">
    <div class="logo">
      <div class="logo-dot"></div>
      MARKET DAILY
    </div>
    <div class="header-meta">
      <span class="live-badge">● LIVE</span>
      <span>更新：{date_str} {weekday_str}</span>
      <span>數據：Bigdata.com × Claude</span>
    </div>
  </div>
  <div class="date-nav" id="dateNav">
    <!-- 由 JS 動態生成 -->
  </div>
</header>

<!-- Main -->
<div class="container">
  <div class="layout">

    <!-- 主內容 -->
    <div class="main-content">
      <div class="report-hero fade-in">
        <h1>🇺🇸 美股機構日報</h1>
        <div class="accent-line"></div>
        <div class="subtitle">
          <span>📅 {date_str} {weekday_str}</span>
          <span>🤖 Claude AI × Bigdata.com</span>
          <span>⏰ 每日 07:00 自動更新</span>
          <span>📊 全自動零手動</span>
        </div>
      </div>

      <div class="report-body fade-in" id="reportContent">
        {report_html}
      </div>
    </div>

    <!-- 側邊欄 -->
    <div class="sidebar">
      <div class="sidebar-card">
        <div class="sidebar-title">歷史日報</div>
        <div id="historyList"></div>
      </div>
    </div>

  </div>
</div>

<!-- Footer -->
<div class="footer">
  <p>🇺🇸 美股機構日報 ｜ 自動生成於 {date_str}</p>
  <p style="margin-top:6px">⚠️ 本報告為 AI 自動生成之資訊整理，不構成任何投資建議。投資涉及風險，請自行評估。</p>
  <p style="margin-top:6px; color:#334155">Powered by Claude AI × Bigdata.com × GitHub Actions</p>
</div>

<script>
// ── 歷史日報數據 ──────────────────────────────────────────────
const HISTORY = {json.dumps(history, ensure_ascii=False)};

// ── 渲染歷史清單 ─────────────────────────────────────────────
function renderHistory() {{
  const nav = document.getElementById('dateNav');
  const list = document.getElementById('historyList');
  
  HISTORY.forEach((item, i) => {{
    // 上方日期按鈕
    const btn = document.createElement('button');
    btn.className = 'date-btn' + (i === 0 ? ' active' : '');
    btn.textContent = item.date.slice(5) + ' ' + item.weekday;
    btn.onclick = () => switchReport(i, btn);
    nav.appendChild(btn);
    
    // 側邊歷史列表
    const li = document.createElement('div');
    li.className = 'history-item' + (i === 0 ? ' active' : '');
    li.innerHTML = `<div class="history-date">${{item.date.slice(5)}}</div><div class="history-day">${{item.weekday}}</div>`;
    li.onclick = () => switchReport(i, null, li);
    list.appendChild(li);
  }});
}}

// ── 簡單 Markdown 轉 HTML ────────────────────────────────────
function mdToHtml(text) {{
  let html = text;
  // 標題
  html = html.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
  // 粗體/斜體
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
  html = html.replace(/`(.+?)`/g, '<code>$1</code>');
  // 引用
  html = html.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>');
  // 分隔線
  html = html.replace(/^---+$/gm, '<hr>');
  // 清單
  html = html.replace(/^[-•] (.+)$/gm, '<li>$1</li>');
  html = html.replace(/^\d+\. (.+)$/gm, '<li class="num">$1</li>');
  // 表格（簡化處理）
  const lines = html.split('\\n');
  let result = [];
  let inTable = false;
  let firstRow = true;
  for (let line of lines) {{
    if (line.trim().startsWith('|') && line.trim().endsWith('|')) {{
      if (!inTable) {{ result.push('<div class="table-wrap"><table>'); inTable = true; firstRow = true; }}
      if (line.replace(/[|-:\\s]/g, '') === '') continue; // 分隔行
      const cells = line.split('|').slice(1,-1).map(c=>c.trim());
      const tag = firstRow ? 'th' : 'td';
      result.push('<tr>' + cells.map(c=>`<${{tag}}>${{c}}</${{tag}}>`).join('') + '</tr>');
      firstRow = false;
    }} else {{
      if (inTable) {{ result.push('</table></div>'); inTable = false; firstRow = true; }}
      result.push(line || '<br>');
    }}
  }}
  if (inTable) result.push('</table></div>');
  return result.join('\\n');
}}

// ── 切換日報 ─────────────────────────────────────────────────
function switchReport(index, btnEl, listEl) {{
  const content = document.getElementById('reportContent');
  content.style.opacity = '0';
  content.style.transform = 'translateY(8px)';
  
  setTimeout(() => {{
    const item = HISTORY[index];
    content.innerHTML = mdToHtml(item.content);
    content.style.transition = 'all 0.3s ease';
    content.style.opacity = '1';
    content.style.transform = 'translateY(0)';
    
    // 更新 active 狀態
    document.querySelectorAll('.date-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.history-item').forEach(l => l.classList.remove('active'));
    if (btnEl) btnEl.classList.add('active');
    if (listEl) listEl.classList.add('active');
    
    // 滾到頂部
    window.scrollTo({{ top: 0, behavior: 'smooth' }});
  }}, 200);
}}

// ── 初始化 ───────────────────────────────────────────────────
renderHistory();
</script>
</body>
</html>"""

# ── 寫出 index.html ───────────────────────────────────────────
output_path = Path("index.html")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html_template)

print(f"✅ index.html 已生成（{output_path.stat().st_size / 1024:.1f} KB）")

# ── 生成 README ───────────────────────────────────────────────
readme = f"""# 🇺🇸 美股機構日報

> 每天早上 7:00（台灣時間）自動生成，由 Claude AI × Bigdata.com 驅動

**最後更新：{date_str} {weekday_str}**

## 📊 查看日報

➡️ **[點此查看最新日報](https://你的GitHub帳號.github.io/stock-dashboard/)**

## 🔧 技術架構

- **數據來源**：Bigdata.com（FMP・RavenPack・Wall St. Rank）
- **AI 分析**：Claude claude-sonnet-4-20250514（Anthropic）
- **自動化**：GitHub Actions（每天 23:00 UTC = 台灣 07:00）
- **部署**：GitHub Pages（免費靜態託管）

## ⚠️ 免責聲明

本報告為 AI 自動生成之資訊整理，不構成任何投資建議。投資涉及風險，請自行評估並承擔責任。
"""

with open("README.md", "w", encoding="utf-8") as f:
    f.write(readme)

print(f"✅ README.md 已生成")
print(f"🎉 完成！所有檔案已準備好，等待 git push 部署。")
