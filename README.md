# PropTech AI Copilot

> 推薦展示方式：**Next.js + FastAPI**。  
> `app.py` 的 Streamlit 版本保留為 **legacy backup demo**。

這是一個台灣房仲 AI PropTech 競賽展示型 MVP。核心主線是 TaxOracle 稅務先知系統；Market Insight、Aegis-Credit 與 LexProp 則是 Lite 展示模組。

## 最短啟動方式

開啟兩個 Windows PowerShell 視窗。

第一個視窗啟動 backend：

```powershell
.\scripts\start_backend.ps1
```

第二個視窗啟動 frontend：

```powershell
.\scripts\start_frontend.ps1
```

瀏覽器開啟：

```text
http://localhost:3000
```

展示前可執行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check_demo.ps1
```

## 專案亮點

- TaxOracle 使用 `TX001` 到 `TX009` deterministic rule engine 判斷資格。
- `eligibility_status` 與 `risk_score` 分離，風險分數不會取代法規結論。
- AI 僅根據 structured result 產生中文說明，不會自行判斷資格或新增法規結論。
- 沒有 `OPENAI_API_KEY` 時仍可使用固定模板 fallback。
- 提供 Rule Trace、缺件清單、五年列管提醒、SQLite History 與可下載 HTML report。
- Next.js 產品化展示 UI 與 Streamlit 備援版共存。

## 模組

| 模組 | 定位 |
| --- | --- |
| TaxOracle | 稅務資格快篩、風險燈號、Rule Trace、五年列管與 HTML report |
| Market Insight Lite | mock 區域行情、六期趨勢、POI 與 ESG / SDG 11 Lite |
| Map Insight v5 | 縣市／鄉鎮／路段快速選擇、手動地址搜尋、生活機能指標卡與三種底圖 |
| Aegis-Credit Lite | 房貸風險展示型 heuristic，搭配中央銀行 OpenData 五大銀行月資料作市場背景參考 |
| 銀行牌告利率 | 中央銀行 OpenData set_id=9464；依銀行查詢房貸相關牌告利率，失敗時使用展示資料 |
| 房價估算 | 使用輕量實價登錄 sample 進行可比成交估算，顯示估值區間與信心分數 |
| Aegis-Credit Lite | 展示型房貸風險 heuristic，不代表銀行核貸 |
| LexProp Lite | 公開判決摘要模糊比對，不輸出完整門牌與個資 |
| History | SQLite 保存並查看 TaxOracle 分析紀錄 |

## TaxOracle Demo Cases

| Demo case | 預期資格 | 預期燈號 |
| --- | --- | --- |
| `DEMO-LOW` | `eligible` | `green` |
| `DEMO-MEDIUM` | `manual_review` | `yellow` |
| `DEMO-HIGH` | `not_eligible` | `red` |

## 完整啟動指令

Backend：

```powershell
python -m uvicorn backend.api_main:app --reload
```

Frontend：

```powershell
cd frontend_next
npm.cmd install
npm.cmd run dev
```

Frontend 預設透過 `frontend_next/.env.example` 說明的設定連線：

```text
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Streamlit legacy backup demo：

```powershell
streamlit run app.py
```

## 競賽展示流程

1. 從 Dashboard 說明競賽展示模式三步驟。
2. 進入 TaxOracle，選擇低風險案例並執行分析。
3. 說明資格狀態、燈號、Rule Trace、缺件與五年列管。
4. 強調 AI 只負責解釋，資格由 deterministic rule engine 判斷。
5. 一鍵下載 HTML report。
6. 快速帶過三個 Lite 模組。

## 目前限制

- 目前僅使用 mock CSV，不串接政府或外部即時 API。
- Map Insight 可由 backend 使用 Google Places (New) 查詢交通、學校、公園、醫療、商圈與餐飲；API key 不會傳到前端。
- 未設定 `GOOGLE_MAPS_API_KEY`、Google timeout、quota 或服務錯誤時，Map Insight 自動使用相同 schema 的 mock fallback。
- Map Insight v2 的生活機能分數同時考慮設施類別、數量與距離，並提供最近設施及客戶溝通建議；結果不代表正式估價、投資或交通分析。
- Map Insight v3 透過 `GET /map/google-health` 安全顯示 Google Geocoding / Places 啟用狀態，不回傳 API key；有 key 時地址搜尋優先使用 Google Geocoding。
- 前端底圖可切換 OpenStreetMap、CartoDB Positron 與 Esri World Imagery，皆不需要 Google Maps frontend key。
- 評分準則固定顯示六類設施權重與距離級距，方便理解分數來源。
- Map Insight v5 可透過正式專案內的台灣路名資料快速選擇縣市、鄉鎮市區與路段，也保留完整地址手動搜尋。
- 生活機能總分分為極佳、良好、普通、偏弱、不足五級；六大指標各自顯示權重、分數、POI 數量、最近距離與文字說明。
- Aegis-Credit 的市場房貸利率參考來自中央銀行 OpenData「五大銀行存放款利率歷史月資料」；資料為月資料，不代表銀行實際核貸利率。
- 央行 OpenData 無法使用時會自動切換展示資料 fallback，不影響房貸風險分析。
- 銀行牌告利率僅供市場背景參考，不代表實際核貸利率；房價估算不代表正式鑑價、銀行估價或成交保證。
- TGOS、TDX、PLVR 真實 adapter 尚未啟用。
- 未來啟用地圖 adapter 時，API key 必須由 `.env` 或部署環境變數提供，不可寫入程式或 commit。
- 不提供正式報稅、法律、估價、投資或銀行核貸判斷。
- 不提供登入、PDF、RAG 或複雜地圖功能。
- Lite 模組以概念展示為主，不代表正式產品承諾。

## 免責聲明

本系統僅供房仲與客戶進行初步稅務風險溝通與文件準備參考，不構成法律、稅務或申報保證。正式資格與稅額仍以主管稅捐機關、最新法令函釋及專業人士審查為準。

## 測試

Python：

```powershell
pytest
```

Next.js production build：

```powershell
cd frontend_next
npm.cmd run build
```

## 常見錯誤排除

- Backend 沒開：執行 `.\scripts\start_backend.ps1`，再確認 `http://localhost:8000/health`。
- Port `8000` 或 `3000` 被占用：關閉舊程序後重新啟動。
- `npm install` 失敗：確認 Node.js 與 npm 可用，再執行 `cd frontend_next` 與 `npm.cmd install`。
- 沒有 Docker CLI：直接使用 PowerShell 腳本或上述手動指令，不需安裝 Docker 才能展示。

## Future Roadmap

- 串接經授權且可稽核的資料來源，保留 mock fallback。
- 增加規則版本控管、人工覆核流程與操作稽核。
- 擴充 CRM、案件協作與報告管理能力。
- 依正式需求評估政府資料介接與資安治理。

## 文件

- [競賽展示講稿](docs/demo_script.md)
- [最終展示檢查清單](docs/final_demo_checklist.md)
- [展示截圖清單](docs/screenshot_plan.md)
- [Legacy 功能盤點](docs/legacy_feature_inventory.md)
## 資料來源與可信度

- 銀行牌告利率使用中央銀行 OpenData `set_id=9464`；服務失敗時切換 13 家金融機構展示資料。牌告資料不代表實際核貸利率。
- 房價估算使用 `data/real_price_sample.csv` 的 72 筆展示型可比成交，採 IQR、相似度加權與 P25/P75；不是完整實價登錄、正式估價或銀行鑑價。
- 房價估算可由後台將人工取得的官方 PLVR OpenData ZIP/CSV 清洗後匯入 Supabase/Postgres；系統不會在 Render runtime 自動下載或執行 ETL。
- Map Insight 定位順序為 Google Geocoding、TGOS、展示資料；周遭設施使用 Google Places 或展示資料。
- `OPERATIONAL` 僅表示店家正常營運，不代表目前正在營業；只有 Google 明確回傳 `openNow` 時才顯示目前營業或休息。
- PLVR adapter 已預留但尚未啟用，不會在部署啟動時下載外部資料。

### 可普及化房價估算

房價估算資料層採 provider 架構，依序嘗試 Supabase/Postgres、SQLite index、`real_price_sample.csv` 與展示資料 fallback。使用者只需輸入估價條件，不需要下載 CSV、ZIP 或執行 ETL。

`GET /valuation/data-status` 會顯示目前資料來源、官方資料期間、最近匯入範圍、官方／展示筆數、覆蓋範圍與更新時間。正式全台版本建議由 GitHub Actions 定期整理官方批次資料，再寫入 Supabase/Postgres；Render runtime 不負責下載或清洗大型資料。

詳見 [房價估算普及化架構](docs/valuation_public_service_architecture.md)。

Supabase/Postgres 建置方式請參考 [Supabase 估價資料庫設定](docs/supabase_valuation_setup.md)。使用 `psycopg[binary]` 作為最小 Postgres driver，避免加入大型 ORM，也避免 Render 需要額外編譯系統套件。

### 手動匯入官方 PLVR OpenData

先套用 `database/migrations/001_add_dedupe_key_to_real_price_transactions.sql` 與 `002_expand_valuation_import_runs.sql`，再以 dry-run 檢查人工取得的買賣實價登錄 ZIP、CSV 或資料夾：

```powershell
python scripts/import_plvr_to_postgres.py --input C:\temp\plvr.zip --city 台北市 --dry-run
python scripts/import_plvr_to_postgres.py --input data/raw/plvr/history --cities 台北市,新北市 --since 2025-01 --until 2026-12 --dry-run
```

確認品質檢查報告後，在本機或受控 CI 設定 `VALUATION_DATABASE_URL` 再執行正式匯入：

```powershell
python scripts/import_plvr_to_postgres.py --input C:\temp\plvr.zip --city 台北市
```

腳本以 `source + dedupe_key` 去重，重複執行不會再次插入相同交易；超過 10,000 筆需明確加入 `--confirm-large-import`。腳本只接受本機檔案，不會下載全台資料；原始 ZIP、完整 CSV 與資料庫連線字串都不可 commit。詳見 [PLVR 歷史資料匯入指南](docs/plvr_historical_import_guide.md)。

正式寫入使用 temporary staging table 分批 upsert，預設 `--chunk-size 200 --progress-every 100 --statement-timeout 30`；可用 `--max-write-rows 100` 先驗證小範圍寫入。

### Rolling 3 年保留與六都擴充

官方 PLVR 採 rolling 3 年保留策略。每季先匯入新資料、檢查 data-status，再以 dry-run 盤點超出保留期間的官方資料；只有維護者明確加入 `--confirm-delete` 才會刪除，展示樣本、社區資料與匯入紀錄不受影響。三年以前若需要長期趨勢，未來將另建統計摘要表。

```powershell
python scripts/prune_valuation_data.py --keep-years 3 --dry-run
```

六都近三年資料建議先對 `data/raw/plvr/pending_liudu/` 執行整體 dry-run，再分桃園、台中、台南、高雄逐城匯入。城市比對支援 `臺／台` 正規化。本階段不在 Render runtime 執行 ETL，也不將 raw ZIP、CSV 或資料庫連線字串 commit。

詳見 [PLVR Rolling 3 年資料保留策略](docs/plvr_retention_policy.md) 與 [PLVR 歷史資料匯入指南](docs/plvr_historical_import_guide.md)。

### 市場趨勢與未來情境

`POST /valuation/trend` 僅使用最近三年內的官方 PLVR OpenData，排除展示樣本、未來月份與異常交易。系統依同路段、同區同型態、同行政區的順序選樣，顯示月／年中位單價、年化趨勢、波動度與 6、12、36 個月保守／中性／樂觀情境。情境年率限制於 -10% 至 +10%，僅供歷史趨勢理解，不代表成交保證、正式鑑價、銀行估價或投資建議。
### 其他縣市 rolling 3 年準備

六都已建立穩定的 rolling 3 年官方 PLVR 流程；其他縣市可沿用同一套 ETL，依基隆／新竹、苗彰投、雲嘉、屏宜花、東部離島與連江等分組先 dry-run，再分批匯入。Importer 僅辨識買賣主檔，並使用 `dedupe_key v2` 與 natural-key duplicate guard 避免重複交易。

Render runtime 不執行 ETL，raw ZIP／CSV 不 commit，DB URL 與任何 secrets 不寫入 repo。完整流程請見 [PLVR 歷史資料匯入指南](docs/plvr_historical_import_guide.md)，後續功能切分請見 [Product Roadmap](docs/product_roadmap.md)。
