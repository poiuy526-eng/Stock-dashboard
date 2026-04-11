# 🇺🇸 美股機構日報 — 自動化網頁儀表板

每天早上 7:00（台灣時間）自動生成，由 Claude AI × Bigdata.com 驅動

---

## 📦 專案結構

```
stock-dashboard/
├── .github/
│   └── workflows/
│       └── daily-report.yml    ← GitHub Actions 排程設定
├── scripts/
│   └── generate_report.py      ← 自動生成腳本
├── index.html                  ← 日報網頁（自動生成）
├── history.json                ← 歷史日報資料（自動生成）
└── README.md                   ← 本說明文件
```

---

## 🚀 設定教學（15 分鐘完成）

### STEP 1：建立 GitHub Repository

1. 前往 https://github.com，登入你的帳號
2. 點擊右上角「+」→「New repository」
3. Repository name 填入：`stock-dashboard`
4. 選擇「Public」（GitHub Pages 免費方案需要 Public）
5. 勾選「Add a README file」
6. 點擊「Create repository」

---

### STEP 2：上傳所有檔案

**方法 A：直接在 GitHub 網頁上傳（最簡單）**

1. 進入你剛建立的 Repository
2. 點擊「Add file」→「Upload files」
3. 把整個 `stock-dashboard` 資料夾的內容全部拖進去
4. 點擊「Commit changes」

**方法 B：用 Git 指令（適合熟悉 Terminal 的人）**

```bash
git clone https://github.com/你的帳號/stock-dashboard.git
cd stock-dashboard
# 把所有檔案複製進來
git add -A
git commit -m "初始設定"
git push
```

---

### STEP 3：取得 Claude API Key

1. 前往 https://console.anthropic.com
2. 用 Google 帳號登入（或註冊）
3. 點擊左側「API Keys」→「+ Create Key」
4. 輸入名稱「美股日報」→「Create Key」
5. 複製金鑰（sk-ant-... 開頭），存到記事本

> ⚠️ API Key 只顯示一次，請立刻儲存！

**費用說明：**
- 新帳號有 $5 免費額度
- 每次生成日報約 $0.02-0.04
- 每月約 $0.60-1.20（非常便宜）
- 建議加入信用卡以免中斷

---

### STEP 4：設定 GitHub Secrets（儲存 API Key）

1. 前往你的 Repository 頁面
2. 點擊上方「Settings」標籤
3. 左側選單點擊「Secrets and variables」→「Actions」
4. 點擊「New repository secret」
5. Name 填入：`ANTHROPIC_API_KEY`
6. Secret 填入：你的 Claude API Key（sk-ant-...）
7. 點擊「Add secret」

---

### STEP 5：啟用 GitHub Pages

1. 在 Repository 的「Settings」頁面
2. 左側選單點擊「Pages」
3. Source 選擇「Deploy from a branch」
4. Branch 選擇「main」，資料夾選「/ (root)」
5. 點擊「Save」
6. 等待約 1-2 分鐘，頁面會顯示你的網址：
   `https://你的帳號.github.io/stock-dashboard/`

---

### STEP 6：手動測試第一次執行

1. 前往 Repository 的「Actions」標籤
2. 左側點擊「每日美股日報自動生成」
3. 右側點擊「Run workflow」→「Run workflow」
4. 等待約 2-3 分鐘
5. 看到綠色勾勾表示成功！
6. 打開你的 GitHub Pages 網址，就能看到日報了

---

## ⏰ 自動執行時間

| 設定時間 | 對應台灣時間 |
|---------|------------|
| UTC 23:00 | 台灣 早上 07:00 |
| 只在週一至週五執行 | 週末不執行 |

---

## 🔧 自訂設定

### 修改執行時間

編輯 `.github/workflows/daily-report.yml`：

```yaml
- cron: '0 23 * * 1-5'
#        分 時  日 月 星期(1-5=週一到週五)
```

常見時間換算（台灣時間 → UTC）：
- 台灣 06:00 = UTC 22:00 → cron: `'0 22 * * 1-5'`
- 台灣 07:00 = UTC 23:00 → cron: `'0 23 * * 1-5'`
- 台灣 08:00 = UTC 00:00 → cron: `'0 0 * * 2-6'`

### 修改監控股票

編輯 `scripts/generate_report.py` 中的 PROMPT，
在「個股數據」那行修改股票代碼即可。

---

## ❓ 常見問題

**Q：Actions 執行失敗怎麼辦？**
A：點擊失敗的執行記錄，查看 Log 找到錯誤訊息。最常見原因是 API Key 設定錯誤。

**Q：網頁顯示舊的內容？**
A：試試強制重新整理（Ctrl+Shift+R 或 Cmd+Shift+R）

**Q：可以看歷史日報嗎？**
A：可以！網頁上方有日期按鈕，可以切換查看最近 30 天的日報。

**Q：可以分享給別人看嗎？**
A：可以，直接分享你的 GitHub Pages 網址即可。

---

## ⚠️ 免責聲明

本報告為 AI 自動生成之資訊整理，不構成任何投資建議。
投資涉及風險，請自行評估並承擔責任。

---

**Powered by Claude AI × Bigdata.com × GitHub Actions**
