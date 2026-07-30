# PropTech AI Copilot 專案盤點與缺口分析

更新日期：2026-06-08  
分析範圍：目前正式專案的 Next.js、FastAPI、Python services/rules、PLVR pipeline 與文件。  
本文件只盤點現況，不代表新增功能已完成。

## 1. 產品現況摘要

目前產品已不只是競賽型 demo。官方 PLVR rolling 3 年資料、可比成交估價、趨勢情境，以及 Map Insight 的 Google Places / mock fallback，已形成可用的資料與決策骨架。

現階段最完整的流程是：

> 找房雷達 → 帶入估價 → 查看可比成交 → 查看趨勢情境 → 分享條件 / 匯出 HTML 摘要

尚未形成完整閉環的部分是：

> 地圖結果未與估價案件共用狀態 → 貸款只有風險 heuristic 與利率背景、沒有月付試算 → 稅費只涵蓋 TaxOracle 重購退稅快篩、沒有買房稅費與持有成本 → 各風險模組尚未彙整成單一案件決策摘要

### 目前資料基礎

- 官方 PLVR：rolling 3 年策略，約 451,672 筆官方交易。
- 展示樣本：約 72 筆，估價服務會明確區分官方與樣本。
- 覆蓋：約 21 縣市、317 行政區、37,549 路段。
- 連江縣有來源檔但有效估價資料為 0，屬可接受的資料覆蓋缺口。
- Supabase/Postgres 為主要估價資料來源；無連線時有 SQLite、sample、mock fallback。

## 2. 已有功能盤點

### 2.1 TaxOracle 稅務快篩

| 項目 | 現況 |
| --- | --- |
| 位置 / 檔案 | `rules/tax_rules.py`、`services/tax_service.py`、`services/llm_service.py`、`services/report_service.py`、`backend/api/routes_taxoracle.py`、`frontend_next/app/page.tsx` |
| 輸入 | 案件編號、客戶名稱，以及自住、設籍、換購期間、所有權、文件與例外事由等布林條件 |
| 輸出 | `eligibility_status`、`risk_score`、signal、TX001–TX009 rule trace、補件清單、五年列管 timeline、AI/fallback 說明、HTML 報告 |
| 真實資料 | 規則邏輯是真實 deterministic rule engine；案件資料目前主要由展示案例或手動條件提供 |
| Demo / mock | 三組 demo case；AI key optional，無 key 使用 fallback 文案 |
| 買房決策價值 | 對換屋與重購退稅情境有清楚、可追溯的資格快篩價值 |
| 下一步產品化 | 將估價案件條件與 TaxOracle 案件共用；新增買方稅費與持有成本模組時，仍保持規則與說明分離 |

### 2.2 Market Insight

| 項目 | 現況 |
| --- | --- |
| 位置 / 檔案 | `services/market_insight_service.py`、`backend/api/routes_market.py`、`data/mock_market_insights.csv`、`frontend_next/app/page.tsx` |
| 輸入 | city、district |
| 輸出 | 平均單價、六期趨勢、交易量、生活機能、ESG Lite、POI breakdown、摘要 |
| 真實資料 | 無；目前為 mock CSV |
| Demo / mock | 完全是展示資料 |
| 買房決策價值 | 可快速建立區域印象，但與官方 PLVR 趨勢資料重疊且可信度較低 |
| 下一步產品化 | 改為行政區比較入口，直接使用官方 PLVR 聚合結果；保留 ESG / SDG 11 概念作為區域補充指標 |

### 2.3 Map Insight

| 項目 | 現況 |
| --- | --- |
| 位置 / 檔案 | `services/map_service.py`、`services/adapters/geocoding_adapter.py`、`services/adapters/google_places_adapter.py`、`backend/api/routes_map.py`、`frontend_next/components/map/geo-map.tsx`、`frontend_next/app/page.tsx` |
| 輸入 | 地址、行政區、路段，或縣市 / 行政區 / 路段快速選擇；POI 類別 |
| 輸出 | 定位中心、800m 半徑、POI markers、六類生活機能分數、最近設施、資料來源與評分準則 |
| 真實資料 | Google Geocoding / Places 在 backend key 可用時啟用；地圖底圖使用 OSM / CartoDB / Esri |
| Demo / mock | 無 key 或 API 錯誤時自動 mock fallback；TGOS / TDX adapter 尚未正式啟用 |
| 買房決策價值 | 可理解生活圈設施與步行距離，是目前最有視覺與客戶溝通價值的補充模組 |
| 下一步產品化 | 從「POI 有多少」升級成「區位優缺點」；接收估價/找房選定路段、比較不同候選區域，並將結果寫入決策報告 |

### 2.4 房價估算

| 項目 | 現況 |
| --- | --- |
| 位置 / 檔案 | `services/valuation_service.py`、`services/valuation_providers/postgres_provider.py`、`backend/api/routes_valuation.py`、`frontend_next/app/page.tsx` |
| 輸入 | city、district、road、building_type、area_ping、building_age_years、floor、選填社區/地址與座標 |
| 輸出 | 估算總價、每坪單價、P25–P75 區間、信心、來源組成、可比成交、估價依據 |
| 真實資料 | Supabase/Postgres 官方 PLVR；provider fallback 支援 SQLite、sample、mock |
| Demo / mock | 官方資料不足時可能使用展示樣本補充，response 會標示來源 |
| 買房決策價值 | 可判斷特定路段與物件條件的合理成交價格範圍 |
| 下一步產品化 | 強化社區/建案識別、議價空間與開價偏離判斷；把結果傳給貸款、稅費、地圖與報告 |

### 2.5 趨勢情境

| 項目 | 現況 |
| --- | --- |
| 位置 / 檔案 | `services/valuation_trend_service.py`、`backend/api/routes_valuation.py`、`frontend_next/app/page.tsx` |
| 輸入 | 區域、路段、建物型態、坪數、屋齡、6/12/36 月 horizon |
| 輸出 | 月/年序列、近期中位單價、年化趨勢、波動度、信心、保守/中性/樂觀情境 |
| 真實資料 | 只使用官方 PLVR，排除 sample/mock、未來月份與 rolling 3 年窗口外資料 |
| Demo / mock | 情境為可解釋公式，不是精準預測 |
| 買房決策價值 | 可用於理解區域價格方向與波動，不應當作成交保證 |
| 下一步產品化 | 將趨勢與目前開價/估價區間結合，形成「價格偏高、合理、偏低」與流動性風險提示 |

### 2.6 找房雷達 Property Finder v1

| 項目 | 現況 |
| --- | --- |
| 位置 / 檔案 | `services/property_search_service.py`、`services/valuation_providers/postgres_provider.py`、`backend/api/routes_valuation.py`、`frontend_next/components/property-finder.tsx` |
| 輸入 | city、districts、預算上下限、坪數上下限、建物型態、屋齡上限、樓層下限 |
| 輸出 | 結果摘要、推薦行政區、推薦路段、符合條件歷史成交 |
| 真實資料 | 只使用 rolling 3 年官方 PLVR |
| Demo / mock | 不使用 sample/mock；不是即時待售物件搜尋 |
| 買房決策價值 | 將「我買得起哪裡」轉成可操作的歷史成交方向 |
| 下一步產品化 | 加入條件保存、候選區域比較、從推薦路段直接前往地圖與貸款試算 |

### 2.7 資料狀態卡

| 項目 | 現況 |
| --- | --- |
| 位置 / 檔案 | `services/valuation_service.py`、`services/valuation_providers/postgres_provider.py`、`frontend_next/app/page.tsx` |
| 輸入 | 無；由 active provider 統計 |
| 輸出 | provider、官方/樣本筆數、raw/effective period、retention、coverage、最近匯入 |
| 真實資料 | Postgres data-status 為真實統計；fallback provider 為本地資料狀態 |
| Demo / mock | fallback 時會反映 sample/mock 狀態 |
| 買房決策價值 | 讓使用者知道估價結論的資料基礎與限制 |
| 下一步產品化 | 保持簡短摘要，詳細覆蓋放折疊或管理文件；避免每次回傳/渲染完整行政區長文 |

目前程式已存在 `coverage_city_count`、`coverage_district_count`、`coverage_road_count`、`coverage_summary`、`coverage_note_short`，前端也優先顯示短摘要。因此此項已從「未完成 P0」轉為「需驗證正式環境效能與相容性的 P0 穩定化」。

### 2.8 分享連結與 HTML 摘要匯出

| 項目 | 現況 |
| --- | --- |
| 位置 / 檔案 | `frontend_next/lib/valuation-share.ts`、`frontend_next/app/page.tsx`、`services/report_service.py` |
| 輸入 | 估價條件、估價結果、趨勢結果、可選找房雷達結果；TaxOracle 另有案件與分析結果 |
| 輸出 | query-string 分享連結、前端 Blob HTML 摘要、TaxOracle backend HTML report |
| 真實資料 | 依當次估價與規則結果 |
| Demo / mock | 無登入、無永久分享紀錄；分享連結只帶條件，不帶結果快照 |
| 買房決策價值 | 可交給家人/客戶查看條件與分析摘要 |
| 下一步產品化 | 統一為「看屋決策摘要」，納入地圖、貸款、稅費與風險，並顯示各資料來源時間 |

### 2.9 Aegis-Credit / 房貸利率

| 項目 | 現況 |
| --- | --- |
| 位置 / 檔案 | `rules/mortgage_rules.py`、`services/mortgage_rate_service.py`、`services/bank_rate_service.py`、`backend/api/routes_lite.py`、`backend/api/routes_mortgage_rates.py`、`backend/api/routes_bank_rates.py` |
| 輸入 | 收入、負債、現金、房屋數、房貸數、物件價格；銀行代碼 |
| 輸出 | heuristic 風險分數、signal、traces、央行五大銀行月資料、銀行牌告利率 |
| 真實資料 | 央行 OpenData；API 失敗時 mock fallback |
| Demo / mock | 風險判斷為展示型 heuristic；前端目前使用預設買方情境 |
| 買房決策價值 | 能補充利率與財務風險背景，但還不能回答「每月要付多少、壓力是否可承受」 |
| 下一步產品化 | 新增頭期款、貸款成數、年限、寬限期、利率敏感度與月付試算，並可直接使用估價結果 |

### 2.10 LexProp 判決風險摘要

| 項目 | 現況 |
| --- | --- |
| 位置 / 檔案 | `rules/legal_risk_rules.py`、`data/mock_judgments.csv`、`backend/api/routes_lite.py`、`frontend_next/app/page.tsx` |
| 輸入 | city、district、masked road、community |
| 輸出 | risk score、match count、summary |
| 真實資料 | 無；mock judgments |
| Demo / mock | 完全是展示型匿名化比對 |
| 買房決策價值 | 展示法律風險概念，但目前無法支援真實案件結論 |
| 下一步產品化 | 改成「交易前風險檢查清單」與需詢問事項；保留判決摘要作為示例證據，而非主結論 |

### 2.11 History、Dashboard、Onboarding、Streamlit 備援

| 功能 | 現況與價值 | 下一步 |
| --- | --- | --- |
| Dashboard 任務首頁 | 有三個 TaxOracle 案例入口、流程與模組入口 | 改成保存同一筆「買房案件」的進度與下一步 |
| Onboarding v2 | 五步驟產品流程動畫，localStorage 控制版本 | 導覽 CTA 應直接建立/載入同一筆決策案件 |
| History | SQLite 保存 TaxOracle 分析歷史 | 擴成跨模組案件紀錄，而非只有 TaxOracle |
| Streamlit `app.py` | legacy backup demo | 保留備援，不再承擔產品主流程 |

### 2.12 PLVR importer / pipeline

| 項目 | 現況 |
| --- | --- |
| 位置 / 檔案 | `scripts/import_plvr_to_postgres.py`、`services/plvr_import_service.py`、`scripts/backfill_dedupe_key_v2.py`、`scripts/prune_valuation_data.py`、`database/`、相關 docs |
| 輸入 | 單一 CSV、ZIP 或資料夾；city/district/road/period/limit 等範圍參數 |
| 輸出 | 正規化官方交易、import report、import runs、data-status |
| 已有防護 | city mapping、官方 CSV 第二列跳過、純土地排除、dedupe_key v2、natural-key duplicate guard、batch/chunk、statement timeout、large import 防呆、dry-run、rolling 3 年 prune |
| 真實資料 | 官方 PLVR OpenData |
| 實際價值 | 是估價、趨勢與找房雷達可信度的核心基礎 |
| 下一步產品化 | 建立排程監控、資料品質告警與匯入摘要；ETL 仍不得在 Render runtime 執行 |

## 3. 目標買房流程缺口

| 流程 | 狀態 | 已有能力 | 目前阻塞點 | 最小可行下一步 |
| --- | --- | --- | --- | --- |
| 1. 找房 | 已完成 v1 | 官方 PLVR 預算/區域/坪數/屋齡篩選、區域與路段推薦、帶入估價 | 不是待售物件；尚無候選比較與保存 | 加入候選區域比較與前往地圖/貸款 CTA |
| 2. 估價 | 已完成核心 | road-first 可比成交、資料來源透明、信心與區間 | 社區識別有限；沒有開價偏離分析 | 接受「開價」輸入，顯示相對估值區間與議價風險 |
| 3. 趨勢 | 已完成核心 | 官方 PLVR rolling 3 年、月/年序列、情境與波動 | 尚未與開價、流動性、行政區比較結合 | 將趨勢摘要轉成決策標籤與比較表 |
| 4. 地圖 | 部分完成 | Google Places / mock、POI、800m、生活機能分數 | 未與找房/估價共用案件；缺少候選區域比較 | 讓找房路段一鍵送到 Map Insight，輸出區位優缺點 |
| 5. 貸款 | 部分完成 | 央行月資料、銀行牌告利率、heuristic 風險 | 沒有頭期款/月付/利率敏感度；前端仍是預設情境 | 做貸款月付試算 v1，使用估價總價預填 |
| 6. 稅費 | 部分完成 | TaxOracle 重購退稅資格快篩 | 無買方契稅、登記、仲介、持有成本等概算 | 做買房稅費與持有成本的透明公式試算 |
| 7. 風險 | 部分完成 | 估價信心、趨勢波動、TaxOracle、Aegis、LexProp | 風險分散在不同模組，無統一案件風險摘要 | 建立決策風險摘要：資料信心、價格、流動性、貸款、稅務 |
| 8. 報告 | 部分完成 | 分享條件、估價 HTML 摘要、TaxOracle HTML report | 兩份報告分離；未納入地圖、貸款、稅費、風險 | 做看屋決策摘要 v2，仍先使用 HTML |

## 4. 「好玩但實質效益不足」的功能轉化

不建議刪除這些功能；應把它們接回同一筆買房案件與決策結果。

| 現有功能 | 目前問題 | 如何接到實際決策 | 所需資料 | 前端調整 | 後端調整 | 優先級 |
| --- | --- | --- | --- | --- | --- | --- |
| Market Insight | mock 摘要與六期趨勢，和官方 PLVR 趨勢重疊 | 改成行政區趨勢與價格帶比較 | 官方 PLVR 聚合 | 候選行政區比較表/卡 | 新增 district comparison 聚合 | P1 |
| Map Insight | 視覺好看，但與找房/估價是分離操作 | 從候選路段直接分析生活圈，輸出區位加減分 | Google Places、geocoding、官方路段 | 顯示「此區優點 / 注意事項 / 前往估價」 | 支援候選比較與摘要輸出 | P0 |
| Aegis-Credit | heuristic 與利率資料未回答實際月付 | 用估價總價、頭期款與利率計算月付與壓力 | 央行/銀行牌告利率、使用者收入負債 | 月付、利率敏感度、負擔率 | 透明公式 calculator | P0 |
| LexProp | mock 判決摘要很難形成真實結論 | 改成交易前應確認清單與風險問句 | mock 判決、未來可接公開資料 | checklist 而非單一分數 | 可先不改或只改輸出結構 | P2 |
| ESG / SDG 11 Lite | 分數來源是 mock，容易被當成裝飾 | 作為區域生活品質輔助，不作估價分數 | POI、公園、步行、公共設施 | 放進 Map Insight 次要指標 | 由真實 POI 衍生可解釋指標 | P2 |
| Dashboard demo cases | 強調展示，但不是使用者案件 | 轉成「開始新案件 / 繼續最近案件」 | 本地或後端案件狀態 | 案件進度與下一步 CTA | 需要案件 session/schema，後續再做 | P1 |
| Onboarding 動畫 | 解釋流程但不保存進度 | 導覽結束建立第一筆決策案件 | 現有模組 metadata | 導覽 CTA 對應真正流程 | 初期不需改 backend | P2 |
| History | 只有 TaxOracle | 顯示找房、估價、地圖、貸款與報告進度 | 案件結果摘要 | 跨模組 timeline | 需統一 case model | P1 |
| HTML 報告 | TaxOracle 與估價摘要分離 | 變成家人/客戶可閱讀的看屋決策摘要 | 各模組摘要與來源時間 | 報告預覽與章節選擇 | 組合 report DTO；不做 PDF | P1 |

## 5. Data-status 問題與建議

### 後端目前回傳

- `active_source`、`is_demo_data`、`is_full_taiwan`
- `official_records_count`、`sample_records_count`
- `raw_official_period_min/max`
- `effective_trend_period_min/max`
- `retention_policy_years`、`retention_cutoff_period`
- `records_outside_retention_count`
- `coverage.cities`、`coverage.districts`、`coverage.roads_count`、`coverage.records_count`
- `coverage_city_count`、`coverage_district_count`、`coverage_road_count`
- `coverage_cities`、`coverage_summary`、`coverage_note_short`
- 最近匯入狀態與資料品質提醒
- 相容欄位 `official_coverage_note`

### 前端目前渲染

- 以 metric tiles 顯示筆數、期間、rolling 3 年、覆蓋數與最近匯入。
- 已優先顯示 `coverage_summary` 與 `coverage_note_short`。
- 已不直接渲染完整 `official_coverage_note`。

### 判斷

此問題的核心修正已存在於目前工作樹，但正式環境仍需驗證：

1. Postgres data-status 是否只傳必要的城市清單，而不是完整行政區長文字。
2. data-status 聚合查詢在 45 萬筆以上資料量時的延遲。
3. coverage 統計是否可做短期 cache。
4. 舊欄位保持相容，但前端永不顯示全文。

因此仍應列為下一關 P0，但工作內容是「效能驗證與收斂」，不是重新新增欄位。

## 6. 工程與產品風險

| 風險 | 影響 | 建議 |
| --- | --- | --- |
| `frontend_next/app/page.tsx` 集中多數頁面與流程 | 後續跨模組整合易產生回歸 | 逐關拆出 valuation、loan、report 等 feature components；避免大重構 |
| 部分中文常數/既有文件疑似編碼亂碼 | UI 文案、報告與維護品質受影響 | 建立 UTF-8 檢查與文案清理關卡，不與功能開發混做 |
| 功能各自有結果，沒有統一案件狀態 | 使用者必須重複輸入，流程斷裂 | 先用前端 shared case state，登入/永久案件留後續 |
| Market Insight 使用 mock，與官方趨勢重疊 | 可信度混淆 | 明確降為輔助，逐步改用官方聚合 |
| Aegis / LexProp 使用展示 heuristic/mock | 容易被誤解為正式核貸/法律判斷 | 保留免責，改為可解釋 checklist 與試算 |
| Google Places 有成本與 quota | 地圖功能不穩定 | 保留 health check、cache、mock fallback 與來源 badge |
| 分享連結只含輸入條件 | 結果會隨資料更新而變化 | 明確標示重新查詢；未來可加入結果時間戳或快照 |

## 7. 結論

目前最有價值的產品骨架不是單一 TaxOracle 或地圖，而是：

> 官方 PLVR 資料基礎 + 找房方向 + 可比估價 + 趨勢 + 可解釋來源

下一步不應繼續擴資料管線，也不應增加孤立 demo。應優先補上「貸款月付試算」，並把找房、估價、地圖、貸款與報告串成同一個可理解的買房決策流程。
