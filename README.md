# 沖繩 Tide Log — 部署 + Notion 連接教學

呢個係一個手機版網頁app，包含「行程」同「記帳」兩頁，記帳資料可以連去你自己嘅Notion database。
以下步驟你自己喺自己電腦做一次就得，唔需要識寫code，跟住做就可以。

---

## 第一步：喺 Notion 開一個 Database

1. 開 Notion，新建一個 **Database (Table)**，改名叫「沖繩旅費記帳」。
2. 將欄位（properties）改成**同以下完全一樣**嘅名同type（大小寫、全形/半形要一致）：

| 欄位名稱 | 類型 |
|---|---|
| Name | Title（預設果個就係） |
| Day | Select |
| Date | Date |
| Category | Select |
| Amount | Number |
| Currency | Select |
| Payer | Select |
| Note | Text |

   Select 嗰幾欄唔使預先加選項，第一次新增資料時Notion會自動幫你建立。

3. 呢個Database將來會由app幫你自動新增/刪除row，唔使手動填。

---

## 第二步：攞 Notion API Token

1. 去 https://www.notion.so/my-integrations
2. 撳 **+ New integration**，改名「Tide Log App」，Workspace揀返你自己個。
3. 撳「Submit」之後，會見到一串 **Internal Integration Secret**（開頭係`ntn_`或`secret_`），複製低，呢個就係你嘅 `NOTION_TOKEN`。
4. 返去你個「沖繩旅費記帳」Database頁面，撳右上角 **⋯** → **Connections** → 揀返你啱先建立嗰個「Tide Log App」，等佢有權限讀寫呢個database。

## 第三步：攞 Database ID

1. 開返你個Database頁面，睇網址列（URL），格式大約係：
   `https://www.notion.so/xxxxxxxxxxxxxxxxx?v=yyyyyyy`
2. `xxxxxxxxxxxxxxxxx`嗰32位英數字就係你嘅 `NOTION_DATABASE_ID`。

---

## 第四步：部署去 Vercel（兩個方法揀一個）

### 方法A：用 Vercel CLI（最簡單，唔使開GitHub）

1. 你部電腦要先裝咗 Node.js（https://nodejs.org 揀LTS版本裝）。
2. 打開Terminal（Mac）或CMD（Windows），入去呢個資料夾：
   ```
   cd 呢份okinawa-app資料夾嘅路徑
   ```
3. 裝Vercel CLI：
   ```
   npm install -g vercel
   ```
4. 登入（會開瀏覽器畀你登入/註冊Vercel帳戶，免費）：
   ```
   vercel login
   ```
5. 部署：
   ```
   vercel --prod
   ```
   佢會問幾條問題，全部一路Enter用預設就得（Set up and deploy? Yes / Link to existing project? No / project name隨你 / 其他預設）。
6. 部署完成後，Terminal會顯示一個網址，例如 `https://okinawa-tide-log.vercel.app`，呢個就係你嘅app網址。

### 方法B：用 GitHub + Vercel Dashboard（如果你識用GitHub）

1. 將呢個資料夾推上一個新嘅GitHub repo。
2. 去 https://vercel.com/new，登入後揀「Import Git Repository」，揀返你嗰個repo。
3. Framework Preset揀 **Other**，其他設定用預設，撳Deploy。

---

## 第五步：喺 Vercel 設定 Notion 環境變數

1. 去 https://vercel.com/dashboard，揀返你個project。
2. 上面menu撳 **Settings** → 左邊揀 **Environment Variables**。
3. 加兩條：
   - `NOTION_TOKEN` = 你第二步攞到嗰串secret
   - `NOTION_DATABASE_ID` = 你第三步攞到嗰32位ID
4. 撳Save，然後返去 **Deployments** tab，揀最新嗰個部署，撳 **⋯ → Redeploy**（要redeploy先會生效）。

---

## 第五步之二：設定「每日家庭留言」（comment box，sync 上 Notion）

行程頁每一日底部有個「📝 家庭留言 / 太太備註」框，太太打完撳「儲存」就會 sync 上 Notion，兩部電話共用。要開通呢個功能：

1. 喺 Notion **新建一個 Database (Table)**，改名叫「沖繩行程 Comments」。
2. 將欄位改成**同以下完全一樣**（大小寫要一致）：

   | 欄位名稱 | 類型 |
   |---|---|
   | Day | Title（預設嗰個 title 欄，改名做 `Day`）|
   | Comment | Text |

3. 喺呢個 Database 頁面右上角 **⋯ → Connections**，揀返你之前建立嗰個「Tide Log App」integration（同記帳共用同一個 token，唔使開新的）。
4. 睇網址攞 **Database ID**（`notion.so/xxxxxxxx...?v=...` 入面 `?` 之前嗰 32 位）。
5. 去 Vercel → 你個 project → **Settings → Environment Variables**，加一條：
   - `NOTION_COMMENTS_DATABASE_ID` = 頭先攞到嗰 32 位 ID
   （`NOTION_TOKEN` 已經有咗，唔使再加。）
6. 撳 Save → **Deployments** → 最新嗰個 → **⋯ → Redeploy**。

設定好之前，個框仍然見到，但撳儲存會顯示「Notion 未設定」。設定好之後，每日儲存會用嗰日做 key（`Day 1`…`Day 8`），同一日再存會覆蓋。

---

## 第六步：喺日本手機用（Add to Home Screen）

1. 用手機Safari（iPhone）或Chrome（Android）開返你個Vercel網址。
2. Safari：撳分享圖示 → 「加至主畫面」。Chrome：撳右上角 ⋮ → 「加到主畫面」。
3. 之後個icon會好似正常App咁喺手機主畫面度，離線都可以睇行程（記帳部分需要網絡先可以同步Notion，但本機記低係唔使網絡㗎）。

---

## 用法

- **行程頁**：同你之前個HTML一樣，可以睇7日行程、地點連結、車程。
- **記帳頁**：
  - 撳右下角 **＋** 新增一筆支出，揀Day、分類、金額、邊個俾錢。
  - 所有記錄**即刻存喺手機本機**（唔使網絡都用到，適合日本outdoor冇wifi時記低）。
  - 想同步去Notion，撳「☁️ 同步去 Notion」，會將未同步嘅記錄一次過上載。
  - 想喺第二部裝置（例如老公部手機）睇返啲記錄，喺嗰部裝置撳「⬇️ 由 Notion 載入」。
  - 頂部可以自行調匯率（HKD⇄JPY），同輸入預算，會有進度bar。

---

## 如果Notion連接有問題

- 記帳頁最底會有狀態提示，如果見到「⚠️」，通常係：
  1. Vercel環境變數未設定好或未redeploy
  2. Notion database未share畀你個integration（返去第二步第4點）
  3. Database欄位名同類型同上面表格對唔上
- 淨係想試吓app介面，唔使Notion都可以，記錄會一直存喺手機本機。
