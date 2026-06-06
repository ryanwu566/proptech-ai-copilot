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
| Map Insight | Google Places 周遭生活機能查詢；未設 key 或外部服務異常時自動使用 mock fallback |
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
