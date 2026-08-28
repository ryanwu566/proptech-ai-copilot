# PropTech AI Copilot × iTaiwan 深度工作模式稽核 v1

> 稽核日期：2026-08-27
> PropTech 稽核基準：`main` / `bbd95f792e6777ebc5c0d343415870368a0a6a93`（2026-08-24）
> 範圍：Audit + Architecture + Roadmap；本次未修改功能、資料庫、部署或 production behavior
> iTaiwan 證據範圍：只採 Gold Swagger 官方產品頁、官方更新與官方使用案例；未下載或逆向工程 Windows 程式

## 判讀方法與證據標記

本報告刻意區分「有程式碼」與「已在正式環境可用」，也區分 iTaiwan 官方說明與獨立實機驗證。

| 標記意義        |                                                             |
| ----------- | ----------------------------------------------------------- |
| `CODE`      | 從目前 commit 的 component、service、route、model 或 migration 直接確認 |
| `DOC`       | repo 的 active documentation；若與 code 衝突，以 code 為準            |
| `TEST`      | 本次實際執行，或 repo 內可檢查的測試契約；fixture 不等於真實 provider 驗證           |
| `OFFICIAL`  | Gold Swagger 或政府／服務提供者的官方頁面                                 |
| `INFERENCE` | 由已確認操作順序做的產品架構推論，不宣稱是競品內部實作                                 |
| `UNKNOWN`   | 官方資料與 repo 都不足，不能合理確認                                       |

本次實際驗證結果：Next.js `typecheck` 通過；production build 通過；ESLint 為 0 errors、27 warnings。執行環境沒有 `pytest`，所以本次沒有把 Python tests 標成「已執行通過」。repo 既有 terrain tests 多使用 fake、fixture、monkeypatch 或 static contract，不能證明真實官方 provider 或全臺 coverage。[P-TEST]

### 核心證據索引

**PropTech repo**

- `[P-01]` `docs/README.md`、`docs/product-capability-surface-v1.md`
- `[P-02]` `docs/property-case-decision-system-v1.md`、`frontend_next/lib/property-case.ts`
- `[P-03]` `frontend_next/lib/case-storage.ts`、`frontend_next/lib/case-comparison.ts`
- `[P-04]` `frontend_next/lib/guided-journey.ts`、`frontend_next/lib/experience-architecture.ts`、`frontend_next/app/page.tsx`
- `[P-05]` `backend/api/*.py`、`backend/api_main.py`
- `[P-06]` `services/property_search_service.py`、`services/valuation_service.py`、`services/valuation_providers/`
- `[P-07]` `services/market_insight_service.py`、`docs/market-data-foundation-v1.md`、`docs/plvr/*`
- `[P-08]` `services/map_service.py`、`services/location_resolver.py`、`services/location_insight_service.py`
- `[P-09]` `docs/terrain-disaster-risk-audit-v1.md`、`services/terrain_risk_service.py`、`services/terrain_risk_providers/`
- `[P-10]` `backend/api/routes_parcel_geometry.py`、`services/parcel_geometry.py`、`frontend_next/components/terrain-risk-analysis.tsx`
- `[P-11]` `services/llm_service.py`、`frontend_next/lib/risk-summary.ts`、`frontend_next/components/viewing-decision-panel.tsx`
- `[P-12]` `database/migrations/*.sql`、`docs/supabase_valuation_setup.md`
- `[P-13]` `services/tax_service.py`、loan/holding-cost routes and services

**iTaiwan 官方**

- `[I-01]` [iTaiwan 官方產品頁](https://www.goldswagger.com.tw/products/iTaiwan)
- `[I-02]` [產品推出與基礎工作流](https://www.goldswagger.com.tw/news/1)
- `[I-03]` [團隊拜訪管理／CRM 更新](https://www.goldswagger.com.tw/news/6)
- `[I-04]` [老屋圖層與基地測量](https://www.goldswagger.com.tw/news/7)
- `[I-05]` [土地／建物謄本、團隊紀錄與下載](https://www.goldswagger.com.tw/news/8)
- `[I-06]` [Chrome「問問 Gemini」輔助看謄本](https://www.goldswagger.com.tw/news/10)
- `[I-07]` [iTaiwan × Gemini 土地分析案例](https://www.goldswagger.com.tw/news/11)
- `[I-08]` [都市更新情報圖](https://www.goldswagger.com.tw/news/12)
- `[I-09]` [15 品牌房仲銷售案件](https://www.goldswagger.com.tw/news/13)
- `[I-10]` [門牌找建號、建物 XLSX、土地上色](https://www.goldswagger.com.tw/news/14)
- `[I-11]` 商業方案與額度：[金流／免費體驗早期公告](https://www.goldswagger.com.tw/news/2)、[付費會員上線](https://www.goldswagger.com.tw/news/4)、[每日 523 筆說明](https://www.goldswagger.com.tw/news/5)
- `[I-12]` 官方喵將軍使用案例：[地籍／分區／實價](https://www.goldswagger.com.tw/general-meow/episode-001)、[範圍分析](https://www.goldswagger.com.tw/general-meow/episode-002)、[土地釘選與案件集合](https://www.goldswagger.com.tw/general-meow/episode-003)、[疑似工廠圖層](https://www.goldswagger.com.tw/general-meow/episode-004)

Gold Swagger 新聞編號 1–14 已逐筆檢視。與 capability/workflow 直接相關者納入上列證據；新聞 3（專欄發布）與 9（會員贈送活動）屬內容／促銷公告，不把它們計成功能。新聞 2 的「付費尚未開放」已被新聞 4–5 與後續 title 點數更新取代，只作版本歷史，不當目前狀態。

---

# 1. Executive Summary

## 結論先行

iTaiwan 的核心不是「更多查詢工具」，而是把專業工作中的同一個標的固定在地圖與地政身分上，讓使用者持續往下工作：定位土地、辨識地號與地上建物、疊圖、測量、看分區／都更／實價／在售供給、調謄本、記錄地主或屋主接觸、分享團隊、匯出成果。它的優勢是 **Property Identity + Map Workspace + Professional Continuity**。[I-01][I-03][I-05][I-10]
PropTech AI Copilot 的核心則是買方決策流程：從官方 PLVR 歷史成交篩選，往區位、地勢參考、可比成交估價、貸款／持有成本／稅務快篩走，最後用保守規則整理成「值不值得進一步看」並保存、比較、列印。它的優勢是 **Market Evidence → Valuation → Affordability/Risk → Decision**。[P-04][P-06][P-11][P-13]
兩邊不是功能數量上的直線競爭，而是工作模型不同：

- iTaiwan 是「先鎖定真實土地／建物，再持續調查與開發」。
- PropTech 是「先輸入買方條件／地址，再聚合分析結果做判斷」。

目前 PropTech 最大缺口不是少一個 GIS 圖層，而是沒有一個持久、可確認、可關聯的 **Property Identity Layer**。現有 `PropertyCase` 是瀏覽器內的決策摘要，最多 10 件，沒有 canonical parcel/building/listing identity、團隊、文件或 ownership graph；Postgres 主要承接 PLVR、市場 read model、pilot evidence 與 tax history，沒有 Property/Case/CRM workspace schema。[P-02][P-03][P-12]
因此最合理的整合不是把 iTaiwan 功能逐一塞進首頁，而是建立一個共用後端：

```
Intake
  → Candidate Resolution
  → Human Confirmation
  → Property Entity Graph
  → Task-specific Evidence Plan
  → Evidence Acquisition (parallel lanes)
  → Evidence Quality Gate
  → AI / deterministic reasoning
  → Decision or Professional Action
  → Case / Compare / Report / CRM
```

同一套 graph 對外提供兩個任務模式：

- **Consumer Mode**：「幫我判斷這間房」，隱藏專業複雜度，保留確認身分與關鍵缺件。
- **Professional Mode**：「我要研究這個土地／建物／基地／案件」，開啟 Parcel、Building、Planning、Title、Listing、CRM 與團隊工作台。

## 關鍵決策

1. `PropertyCase` 應升級，但不是把它膨脹成一張萬能表；應拆成穩定的 `PropertyEntity` 與任務型 `Case`，用 typed relations 組成 Case Graph。
2. Property Resolution 必須回傳 candidates、來源、confidence、衝突與可確認狀態；地址、門牌、地號、建號不是一對一。
3. 先做 identity、durable case/evidence、parcel/building 關聯；再碰 title procurement、跨品牌 listing aggregation 與完整 CRM。
4. 不正面複製 iTaiwan 已成熟的原始查詢廣度；以證據可追溯、差異偵測、估價／資金／風險整合與 AI synthesis 拉開差距。
5. iTaiwan 官方明確說 Gemini 是 Chrome 外部搭配，不是內建 AI，也不替使用者完成受控的 decision synthesis。[I-06][I-07]

---

# 2. Current PropTech AI Copilot Architecture

## 2.1 系統形狀

| Layer    | 現況                                                                                                       | 判定                             |
| -------- | -------------------------------------------------------------------------------------------------------- | ------------------------------ |
| Frontend | Next.js 16 / React 19；主頁整合 guided journey 與進階工具；案件另有 `/cases/[caseId]`                                   | `CODE`，本次 build 通過             |
| Backend  | FastAPI，routes 包含 valuation、market、map、location、terrain、parcel geometry、loan、holding、tax、commute、pilot 等 | `CODE`                         |
| Data     | Postgres／Supabase 風格設定，但 app 以 server-side `psycopg` 存取；沒有前端 Supabase client                             | `CODE`                         |
| Market   | 官方 PLVR batch → transaction facts / aggregate read models → property search、market、valuation             | `CODE`；正式可用依部署資料庫與 freshness   |
| Spatial  | 地址／座標定位、POI、terrain adapters、request-scoped parcel upload；官方 cadastral vector disabled                   | 混合 `ready/partial/unavailable` |
| Case     | React runtime/session events + localStorage saved cases；沒有 server case store                             | `CODE`，單機單瀏覽器                  |
| AI       | 決策摘要為 deterministic TypeScript rules；Python LLM service 固定模板，外部 API 未啟用                                  | `CODE`，不是 production LLM       |

## 2.2 實際前端資訊架構

主流程有五個 stage，而不是 repository 中所有 route 的平鋪列表：[P-04]

1. **Property**：Property Finder／歷史成交方向。
2. **Location**：Location Insight、Terrain Risk、Commute、Market context。
3. **Price**：Valuation、趨勢、comparables。
4. **Affordability**：Loan、Holding Cost、TaxOracle。
5. **Decision**：Viewing Decision、Property Case、Comparison、Print/Export。

stage 可以被使用者跳過，沒有強制 completion gate，也沒有輸入一次就自動跑完全部分析。側欄仍保留 Map Insight Lite、Valuation、Terrain、TaxOracle、Aegis-Credit、Market 等直達入口，所以目前是「任務導向主線 + 工具型旁路」的混合架構。[P-04]

## 2.3 Backend services 與 API surface

| Domain          | 主要 endpoints                                                                      | 真實狀態                                                                        |
| --------------- | --------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Property Finder | `POST /valuation/property-search`                                                 | 只查官方 PLVR 歷史成交，不是現售 listings；provider 不可用即 fail closed [P-06]               |
| Valuation       | `GET /valuation/data-status`; `POST /valuation/estimate`; `POST /valuation/trend` | explainable comps + range；需要 official Postgres，demo mode 才可明示 sample [P-06] |
| Market          | `/market-insights/*` query, segments, comparables, protected refresh/coverage ops | 有正式 read-model 架構，但可用性受匯入、coverage、freshness 與部署 DB 影響 [P-07]               |
| Map             | `/map/search`, `/map/insight`, `/map/nearby`, health                              | geocoding/POI 可用外部 key；否則有 mock/fallback，不能當正式 evidence [P-08]              |
| Location        | `POST /location/resolve`, `POST /location/insight`                                | 可接受地址或座標；provider 與 deployment key 決定品質 [P-08]                              |
| Terrain         | `GET /terrain-risk/sources`, `POST /terrain-risk/analyze`                         | 多數正式風險來源是 placeholder/unavailable；ARDSWC 只有 partial [P-09]                  |
| Parcel geometry | status/upload/consistency/spatial-analyze                                         | 使用者 GeoJSON/KML/SHP ZIP 可算幾何；非官方界址、request-scoped、不持久化 [P-10]               |
| Finance         | loan/holding-cost/Aegis/bank & mortgage rates                                     | loan/holding 是 deterministic；rate/provider 部分依環境或展示資料 [P-13]                |
| TaxOracle       | sources/demo/analyze/report/history                                               | deterministic rule screening；不是法律或正式稅務意見 [P-13]                             |
| Case/Compare    | 無 server case API                                                                 | browser-only [P-03]                                                         |

## 2.4 Current data and persistence model

### Postgres 已存在

- `real_price_transactions`、`community_buildings`、`valuation_import_runs`。
- district/period market aggregates、market metadata、coverage／release 相關表。
- pilot campaigns/sessions/events/feedback/professional reviews。
- `tax_analysis_history`。
- `compact_green` schema 的 PLVR generations、facts、evidence 與 aggregates。[P-12]

### Postgres 不存在

- canonical `properties`、`addresses`、`parcels`、`buildings`、`listings`。
- `property_cases` durable persistence。
- workspace/team/member/role。
- document/title/ownership/encumbrance。
- contact/visit/task/CRM。

### Browser persistence

`case-storage.ts` 使用 `proptech.savedCases.v1`，上限 10 件；`workflowMode` 固定為 `buying_wizard`。保存內容是 compact decision snapshot，會清空歷史交易陣列與 comparables，移除座標、POI 與 raw terrain payload。這有隱私與容量好處，但不可能支撐跨裝置、團隊、文件與專業案件歷史。[P-03]

## 2.5 PLVR architecture

目前最成熟的 data backbone 是 PLVR，而不是 Property Identity：

```
official PLVR batch
  → controlled import / generation
  → normalized transaction facts + evidence
  → market aggregate read model
  → property-search / market-insight / valuation
  → status, freshness, coverage, caveats
```

`property_search_service.py` 明確把結果稱為歷史成交方向，不是假裝目前待售物件；估價以可比交易、community/road/district/city fallback、IQR 與 confidence 產生可解釋區間。這是 PropTech 可以延伸成 evidence-aware AI 的核心資產。[P-06][P-07]

## 2.6 Supabase / Postgres 風險

目前 migrations 沒有找到完整 Property workspace 的 tenant model 或 RLS policies。現行 server-side DB access 不等於未來可安全把 cases、title、contacts 直接暴露給 browser。VNext 若採 Supabase Auth/Data API/Storage，所有 exposed tables 必須明確 grants + RLS，`service_role` 只留 server；敏感文件放 private bucket；PostGIS geometry/geography 應有 GiST index。這也是 Stage 0 必須先做的原因。[Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security)、[PostGIS](https://supabase.com/docs/guides/database/extensions/postgis)、[Storage access](https://supabase.com/docs/guides/storage/security/access-control)

## 2.7 Ready / Partial / Mock / Unavailable

| Capability                    | 稽核狀態                             | 證據與限制                                                                                      |
| ----------------------------- | -------------------------------- | ------------------------------------------------------------------------------------------ |
| Official PLVR property search | **Conditional ready**            | code fail-closed；正式資料庫、coverage、freshness 必須存在 [P-06]                                      |
| Valuation / comparables       | **Conditional ready**            | explainable；official provider 與樣本門檻決定可信 transfer [P-06]                                    |
| Market insight                | **Conditional ready**            | read model 完整；部署資料與 operator operations 未在本次 live 驗證 [P-07]                                |
| Loan / holding cost           | **Ready calculation**            | deterministic；不等於銀行核貸 [P-13]                                                               |
| TaxOracle                     | **Ready screening**              | deterministic rule screening；不是法律／稅務意見 [P-13]                                              |
| Case save / compare / print   | **Ready local-only**             | localStorage 10 件；2–3 case compare；browser print/PDF [P-03]                                |
| Map / POI                     | **Partial / conditional**        | Google/TGOS keys 時可真實；另有 mock fallback [P-08]                                              |
| Location insight              | **Partial / conditional**        | 取決於定位與 POI provider                                                                        |
| Commute                       | **Partial**                      | TDX in-memory snapshot；需 operator refresh，缺 durable normal runtime snapshot                |
| Terrain/disaster              | **Unavailable-majority**         | NLSC terrain、WRA flood、GeologyCloud layers unavailable；ARDSWC partial；audit `NO_GO` [P-09] |
| User-upload parcel polygon    | **Ready prototype**              | upload/validation/area/intersection 可用；非官方、request-scoped、不持久化 [P-10]                      |
| Official cadastral parcel     | **Unavailable**                  | NLSC adapter deliberately disabled/not configured [P-10]                                   |
| Property Identity             | **Unavailable as product layer** | 只有地址／座標 resolver fragments，無 parcel/building/listing graph                                 |
| Professional CRM/team/title   | **Unavailable**                  | 無 domain models、API、persistence                                                            |
| Native generative AI          | **Unavailable**                  | template-only LLM service；decision 是 deterministic rules [P-11]                            |

---

# 3. iTaiwan Current Product Architecture

## 3.1 可由官方資料確認的產品形狀

iTaiwan 是 Windows 桌面應用啟動本機服務後，以瀏覽器作操作介面的地圖型工作工具；官方產品頁要求 Google 登入，目標使用者為房仲、代書、土地開發、都更危老、店長與主管。[I-01]
官方把產品描述成「一張地圖處理三件事」：

1. **找資料**：地圖點選、地址／地號／建號定位，查土地與建物。
2. **看分布**：地籍、段籍、使用分區、都市計畫、實價、老屋、都更、銷售案件等圖層。
3. **留紀錄**：釘選、地主／屋主拜訪、通訊錄、團隊共享、謄本歷史與匯出。[I-01][I-03]

這表示其核心物件不是一份孤立報告，而是「地圖上的土地／建物」；後續所有 title、CRM、listing、team action 都回掛到這個空間身分。[INFERENCE]

## 3.2 官方已確認模組

| 模組         | 官方可確認的能力                                                            | 未知事項                                                  |
| ---------- | ------------------------------------------------------------------- | ----------------------------------------------------- |
| Discovery  | 地址／地號／建號／地圖點選、周邊                                                    | ranking、搜尋演算法、exact coverage unknown                  |
| Identity   | 地址定位 → 土地 → 地上建物 → 門牌／建號確認                                          | 內部 ID、候選 confidence、衝突 resolution unknown             |
| Parcel/GIS | 地籍／段籍／分區等圖層、實際土地形狀、多筆上色、面積／邊長／面寬／路寬／距離                              | vector licensing、geometry source、accuracy SLA unknown |
| Building   | 地上建物清單、樓層 filter、主建物／附屬面積、屋齡、門牌、建號、XLSX                             | 全臺完整度與資料更新頻率 unknown                                  |
| Planning   | 使用分區、都市計畫、老屋年代、8 類都更圖層與案件定位                                         | nationwide consistency、local source mapping unknown   |
| Market     | PLVR、周邊成交、15 品牌 active listing、前次開價／變動、potential duplicate、500m/1km | 刊登資料授權與 acquisition method unknown                    |
| Title      | 土地／建物新謄本、標示／所有權／他項、點數、PDF、查看／複製、個人／團隊歷史                             | 上游合作／介接契約 unknown                                     |
| CRM        | 地主／屋主拜訪、意願、方法、對話、聯絡人、地圖點位、主管 filter、團隊 share                        | 完整 pipeline/task automation unknown                   |
| Export     | PDF、XLSX、team share、history、map locate                              | 外部 public share link／audit retention unknown          |
| AI         | Chrome Gemini 外部讀取畫面與對話                                             | 沒有官方證據支持原生 AI 或受控 decision engine                     |

## 3.3 無法確認的競品內部架構

Gold Swagger 官方資料沒有公開：database schema、backend stack、API contracts、tenant/RLS、entity keys、provider licensing、reconciliation rules、SLAs、model evaluation 或 AI guardrails。本報告不會把上述內容補寫成事實。

## 3.4 商業與使用邊界

2026-02 的早期公告曾說支付／會員／點數尚未開放；2026-03/04 後官方已公告付費會員 30 天 NT$100、每日 523 筆土地／建物查詢，之後新謄本另採調閱點數並與會員資格分開。[I-05][I-11] 這證明查詢額度、會員、title points 是營運 architecture 的一部分，但「523」本身不是應複製的產品能力；真正價值是付費前 identity confirmation、調閱前 personal/team dedupe、失敗退款與完成結算。

---

# 4. iTaiwan End-to-End Workflow

## 4.1 最符合官方證據的主流程

```
Professional intent
  → Address / lot no. / building no. / map movement / map click
  → Map location and land card
  → Confirm parcel identity
  → Open above-ground building list when needed
  → Confirm address + building number
  → Add cadastral / zoning / planning / old-house / urban-renewal layers
  → Measure or combine candidate parcels
  → Review PLVR + current brokerage listings
  → Request or reuse title transcript
  → Pin / color / group target
  → Record landowner / owner visit and contact
  → Share to team and supervisor views
  → Export PDF / XLSX or return to map/history
```

不是每個使用者都會跑完全程。房仲可能在 market/listing/CRM 分支停下；代書可能直走 title；開發團隊會在 multi-parcel/planning/old-house/ownership/CRM 反覆循環。iTaiwan 的價值在於這些分支仍共享同一張地圖與同一土地／建物脈絡。[I-01][I-03][I-05][I-08][I-09][I-10]

## 4.2 十個工作模組

### 4.2.1 Property Discovery

- 以地址定位、地號／建號查詢或直接在地圖移動／點選開始。
- 大範圍先看分布與 cluster，再縮小到土地 card。
- 可由土地 card 看周邊 500m／1km 的成交或在售案件。
- 「地圖點到哪裡就從哪裡繼續」比傳統表單 query 更接近專業探索。[I-01][I-09][I-10]

### 4.2.2 Property Identity

官方更新確認的一條免費 identity flow 是：

```
address locate
  → map moves to place
  → click land
  → land card
  → above-ground building list
  → inspect address / floor / main and attached area / age
  → confirm building number
  → only then request formal information/title if needed
```

門牌找建號本身不計土地／建物查詢額度。這說明 iTaiwan 把 identity confirmation 視為後續付費／正式動作前的必要步驟。[I-10]
但官方沒有說明 one address-to-many buildings、one building-to-many parcels、重編門牌或 conflict confidence 如何建模，這些皆為 `UNKNOWN`。

### 4.2.3 Parcel / GIS Workflow

- 顯示地籍與實際土地形狀，可對多筆土地分別上色、調透明度、保存 map settings、逐筆或全部清除。[I-10]
- polygon 工具圈選候選基地，顯示面積與各邊長；line 工具量測面寬、路寬或任意距離。[I-04]
- 可疊段籍、使用分區、道路、交通、老屋、都更與其他主題圖層。[I-01]
- 官方也明確說測量是前期估算，不是地政鑑界或正式測量成果。[I-04]

### 4.2.4 Building Intelligence

- 從土地開啟地上建物清單，不需另到孤立建物查詢頁。
- 可按樓層過濾；欄位包括縣市、行政區、段小段、建號、門牌、主建物面積、附屬建物面積與屋齡。
- XLSX 匯出是完整建物清單，不受當下樓層 filter 影響。[I-05][I-10]
- 可針對選定建物直接進入建物謄本調閱。[I-05]

### 4.2.5 Planning / Development

- 使用分區與都市計畫回掛於地圖與土地脈絡。
- 老屋按完成年代切成 1975 以前、1975–79、1980–84、1985–89、1990–94，顯示土地中心點並調透明度；僅供前期篩選。[I-01][I-04]
- 都更以 8 個可獨立開關／調透明度的 layer 區分劃定來源與是否已有核定重建事業，並可依案件名稱／位置定位。[I-08]
- 開發工作流是先找區域，再看地籍／老屋／都更／分區，畫候選基地，最後回到 title、ownership、PLVR、周邊與現場。[I-04][I-08]

### 4.2.6 Market Intelligence

- PLVR 解答「過去成交」，房仲銷售案件解答「現在市場拿出什麼、怎麼開價」。[I-09]
- 官方列 15 個品牌，可分建物／土地／車位，地圖以 counts/clusters 與品牌比例呈現。
- detail 顯示圖片、標題、目前／前次總價、價格變動、最後確認時間、單價、面積、屋齡、格局、樓層、車位與原刊登連結。
- 以位置、屋齡、面積分組「可能同物件」，官方沒有宣稱是正式地址 identity。
- 土地 card 的附近銷售案件支援 500m/1km、list/map、品牌 group lazy load。[I-09]

### 4.2.7 Title / Ownership

- 土地：土地 card → 進階資訊 → 調閱新謄本。
- 建物：土地 card → 地上建物清單 → 確認地址與建號 → 調閱選定建物。
- 現行提供「全部調閱」：標示部、所有權部、他項權利部。
- 送出前顯示點數預扣、個人與 team 過往調閱，降低重複花費；失敗退款、完成按實際結果結算。
- 謄本下載頁可 filter、看狀態／owner count／points、直接查看、複製、下載 PDF、分享 team、定位回 map。[I-05]

### 4.2.8 CRM

- 土地或地上建物可建立地主／屋主拜訪。
- 欄位包含日期、方式、意願、對話內容、聯絡方式與聯絡人角色。
- 聯絡資料自動彙整到 address book，從「以 property 找人」延伸到「以人／電話找所有關聯 property」。
- overview 可依物件類型、來源、人員、方式、意願、日期篩選並定位回地圖。
- team permissions、來源切換、成員 filter 與離隊狀態支援主管掌握；地圖點位隨 viewport/filter 更新。[I-03]

### 4.2.9 Export / Collaboration

- PDF：土地／建物查詢或謄本結果的交付與留存。
- XLSX：建物清單與可再分析資料。
- Team：visit/contact/title 分享，個人與團隊來源分離，歷史可回 map。
- Pin/color/history：把探索結果留成工作中的 target set，而非一次性查詢。[I-01][I-03][I-05][I-10]

### 4.2.10 AI

**已確認的 iTaiwan 原生 AI：沒有官方證據。**
官方兩篇文章明確說明：使用者先在 iTaiwan 開啟謄本、分區、都市計畫、PLVR 與周邊 500m 房屋行情，再手動呼叫 Chrome「問問 Gemini」讀取可見畫面。它可協助第一輪摘要與追問，但不是 iTaiwan 內建、不是付費功能，也不替使用者做最終決定。[I-06][I-07]
因此 AI 介入點是「資料已被 iTaiwan 整理並顯示之後」，而不是 ingestion、identity resolution、source validation 或內建 decision synthesis。官方案例甚至包含具高度法律／估價風險的生成式建議，更凸顯正式產品若內建 AI 必須有 evidence boundary、敏感資料同意、引用與拒答規則。

---

# 5. PropTech Current End-to-End Workflow

## 5.1 真正可走的買方流程

```
budget / city / district / road / area / building conditions
  → Property Finder queries official PLVR history
  → user selects a direction / enters an address or property context
  → optional Location Insight / Map / Terrain / Commute checks
  → Valuation uses comparable transactions and produces range/confidence
  → user enters price, loan, income and holding assumptions
  → Loan + Holding Cost + TaxOracle screening
  → deterministic risk summary checks price / data confidence / burden / location
  → Viewing Decision says view / clarify / add data
  → user manually saves local case
  → compare 2–3 local cases
  → browser print / save PDF or HTML summary
```

這條 journey 不是完全自動：使用者需在 stage 間切換或手動查詢；輸入也會分散在 React state、sessionStorage、events 與 localStorage。沒有 canonical identity，所以同一地址在不同 module 的結果主要靠 UI context 與使用者理解維持一致。[P-03][P-04]

## 5.2 從「我有一間房」開始時的實際限制

如果使用者已經有一間特定房子，現況可輸入地址與條件做 location/terrain/valuation/finance，但系統不能正式回答：

- 這個地址對應哪一筆或哪些土地？
- 是哪一個建號／樓層／建物主體？
- 房仲網址是否與該地址／建物同一標的？
- parcel polygon 與 hazard 是否真的相交？
- title、ownership、planning 與 case 是否掛在同一個 property identity？

使用者實際做的是「把一組看似同一間房的分析結果彙整成 case」，而不是「先建立已確認的 property，再由 property 驅動所有查詢」。[P-02][P-10]

## 5.3 Decision synthesis 現況

`risk-summary.ts` 會以估價 confidence、價格是否落在 range、loan/holding income burden、location score、完成度產生 deterministic overall score/signal；缺少核心資料時 score 為 null，unknown 不等於低風險。Viewing Decision 只整理既有結果，不新增黑箱判斷。[P-11]
這是可用的 decision workflow 雛形，但仍不是 generative AI：`services/llm_service.py` 即使存在 `OPENAI_API_KEY` 也只回傳固定模板，註解明說 external API 尚未啟用。[P-11]

---

# 6. Workflow Comparison

| Workflow stage      | iTaiwan 如何做                                         | PropTech AI Copilot 如何做                                     | 較強者            | 原因                                                       | 是否吸收                     |
| ------------------- | --------------------------------------------------- | ----------------------------------------------------------- | -------------- | -------------------------------------------------------- | ------------------------ |
| Intake              | 地址／地號／建號／地圖點選；專業 map-first                          | 預算／區域／路段／坪數／房屋條件；可再輸入地址                                     | 情境不同           | iTaiwan 找特定資產；PropTech 找買方可負擔方向                          | **是：統一 intake**          |
| Identity resolution | 地址 → 地圖 → 土地 → 地上建物 → 門牌／建號確認                       | 地址／座標 resolver fragments；無 parcel/building identity         | iTaiwan        | 後續 title/CRM/listing 都需要穩定標的                             | **P0**                   |
| Parcel              | 地籍、實際土地形狀、多筆上色、pin                                  | 官方 vector disabled；使用者 upload geometry 可算面積/交集              | iTaiwan        | 日常專業 workflow 完整                                         | **P0/P1**                |
| Site measurement    | polygon 面積／邊長、line 面寬／路寬／距離                         | user geometry 能算 area/intersection；無完整基地繪製 workflow         | iTaiwan        | iTaiwan 直接服務土地整合前期                                       | **P1**                   |
| Building            | 土地上的建物清單、門牌／建號／樓層／面積／屋齡、XLSX                        | PLVR transaction attributes，不是 building master              | iTaiwan        | identity 與 title 入口更完整                                   | **P1**                   |
| Planning            | 分區、都市計畫、老屋、8 類都更                                    | PLVR 可能含交易分區；無 planning workspace                           | iTaiwan        | 開發判斷完整且空間化                                               | **P1/P2**                |
| Historical market   | map-based PLVR 與周邊範圍                                | PLVR read model、segments、comparables、freshness、coverage     | PropTech（分析）   | iTaiwan 偏查與分布；PropTech 可比估價與信任狀態更深                       | 保留哲學、補空間視圖               |
| Current listings    | 15 品牌、目前／前次開價、降價、供給、possible duplicate              | Property Finder 明確不是 active listing                         | iTaiwan        | 現況供給資料是 PropTech 空白                                      | **合作／user URL 優先**       |
| Title               | map 內調閱、reuse team history、PDF/share/locate         | 無 title/document domain                                     | iTaiwan        | 已形成完整 transaction workflow                               | 先 upload，再談合法直連          |
| Ownership           | title 標示／所有權／他項，可接 owner visit                      | 無 ownership graph                                           | iTaiwan        | 專業開發必要                                                   | 有權限與個資前提才做               |
| Terrain/hazard      | 產品頁未顯示為核心；官方證據不足                                    | 多 layer architecture，但多數 provider unavailable/partial       | 無勝者            | PropTech product philosophy 更完整，但 production evidence 不足 | 修 trust boundary 後強化     |
| Valuation           | PLVR與區域行情供人工判讀；Gemini 外搭案例                          | explainable comps、range、confidence、official-only transfer   | PropTech       | 受控 deterministic valuation 更成熟                           | 核心差異化                    |
| Finance             | 官方 iTaiwan 核心資料未見貸款／持有成本／tax                        | loan、holding、tax screening                                  | PropTech       | 從物件資訊走到個人可負擔性                                            | 核心差異化                    |
| CRM                 | owner/contact/visit/willingness/map/team/supervisor | Case 有 viewing logs/notes，但 browser-only、非 relationship CRM | iTaiwan        | 能持續累積團隊開發資料                                              | identity + tenant 後做     |
| Collaboration       | team permissions、title/visit/contact history        | 無帳號型 case collaboration                                     | iTaiwan        | PropTech localStorage 無法交接                               | **P0 foundation**        |
| Export              | PDF/XLSX/team share/history                         | HTML/browser print；local compare report                     | iTaiwan        | artifact 與 team reuse 更完整                                | XLSX/PDF service 化       |
| AI                  | 外部 Chrome Gemini 讀畫面，不是內建                           | deterministic decision rules；LLM 未啟用                        | PropTech 有較好起點 | 已有 evidence/unknown 語意可建立受控 AI                           | **P1/P2 differentiator** |
| Decision            | 以資料工作與專業人工判斷為主                                      | explicit viewing decision、next actions、compare/report       | PropTech       | 直接支援「是否值得進一步看」                                           | 保持任務導向                   |

---

# 7. Full Capability Matrix

`✓` = 官方／code 已確認；`△` = 部分、依 provider／部署、或只有較弱相似能力；`—` = 未發現；`?` = 無法確認。

| Capability                  | iTaiwan | PropTech | 工作模式差異／證據                                                               |
| --------------------------- | :-----: | :------: | ----------------------------------------------------------------------- |
| 地址定位                        |    ✓    |     △    | PropTech 有 resolver，但沒有 canonical property resolution [P-08][I-10]      |
| 地號查詢／定位                     |    ✓    |     —    | iTaiwan 可從地圖／地號進入 [I-01]                                                |
| 建號查詢／確認                     |    ✓    |     —    | iTaiwan 由 land → above-ground buildings [I-10]                          |
| 經緯度 input                   |    ?    |     ✓    | iTaiwan 官方未明說 raw coordinate input；PropTech terrain/location 支援         |
| 地圖點選土地                      |    ✓    |     —    | PropTech map 是區位洞察，非 parcel identify                                    |
| 房仲網址 input                  |    —    |     —    | iTaiwan 提供原連結但未說可貼網址作 intake；VNext 可創新                                  |
| 地址／地號／建號關聯                  |    ✓    |     —    | iTaiwan UI flow confirmed；內部 model unknown                              |
| 地籍圖／段籍圖                     |    ✓    |     △    | PropTech 只有 point reference/LANDSECT context；無 authorized parcel vector |
| 宗地 polygon                  |    ✓    |     △    | PropTech 只在 user-upload geometry 時有 polygon                             |
| 多筆土地上色                      |    ✓    |     —    | iTaiwan custom color/transparency/persistence [I-10]                    |
| 土地 pin／標記／集合                |    ✓    |     —    | PropTech cases 不是 map target set                                        |
| polygon 面積／各邊長              |    ✓    |     △    | PropTech backend 可算 uploaded area/intersection，前端偏 terrain evidence     |
| line 距離／面寬／路寬               |    ✓    |     —    | iTaiwan map measurement [I-04]                                          |
| 主題圖層透明度                     |    ✓    |     △    | PropTech map/terrain layers 有狀態，但非專業 layer manager                      |
| 土地上地上建物清單                   |    ✓    |     —    | PropTech 缺 building master                                              |
| 建物樓層 filter                 |    ✓    |     —    | iTaiwan confirmed [I-10]                                                |
| 主／附屬建物面積                    |    ✓    |     △    | PropTech 可能有 PLVR transaction fields，但非 current building inventory      |
| 屋齡／門牌／建號                    |    ✓    |     △    | PropTech 估價 input/PLVR attributes，沒有 canonical building entity          |
| 建物清單 XLSX                   |    ✓    |     —    | iTaiwan full list export [I-10]                                         |
| 使用分區                        |    ✓    |     △    | PropTech PLVR may contain transaction zoning；無 planning evidence module |
| 都市計畫                        |    ✓    |     —    | iTaiwan layer/context                                                   |
| 老屋年代 layer                  |    ✓    |     —    | iTaiwan 5 ranges, point-level preliminary [I-04]                        |
| 都更範圍／進度 layer               |    ✓    |     —    | iTaiwan 8 types + locate [I-08]                                         |
| 疑似工廠等開發 layer               |    ✓    |     —    | 官方專欄只證明高層次 use case；資料／準確性 unknown                                      |
| PLVR 成交查詢                   |    ✓    |     ✓    | iTaiwan map exploration；PropTech official read model                    |
| 周邊 500m／1km 市場              |    ✓    |     △    | PropTech market by region/conditions，不是 parcel-centric radius workspace |
| 市場 segmentation             |    ?    |     ✓    | PropTech segments/comparables endpoints                                 |
| explainable valuation       |    ?    |     ✓    | iTaiwan 官方未證明受控 valuation engine；外部 Gemini 不算                           |
| active listings             |    ✓    |     —    | iTaiwan 15 brands [I-09]                                                |
| 前次開價／降價                     |    ✓    |     —    | listing observation history                                             |
| listing supply / brand mix  |    ✓    |     —    | iTaiwan cluster + brand proportions                                     |
| possible same listing       |    ✓    |     —    | heuristic grouping；不是 formal identity                                   |
| 土地／建物新謄本                    |    ✓    |     —    | iTaiwan paid points workflow [I-05]                                     |
| 所有權／他項權利                    |    ✓    |     —    | title content，不代表 automatic legal conclusion                            |
| personal/team title history |    ✓    |     —    | 避免重複 retrieval                                                          |
| title PDF／copy／map locate   |    ✓    |     —    | iTaiwan confirmed                                                       |
| user document upload        |    ?    |     —    | iTaiwan official未確認；PropTech parcel upload only, not title docs         |
| 地主／屋主 CRM                   |    ✓    |     —    | PropTech viewing logs are case notes, not owner CRM                     |
| contacts/address book       |    ✓    |     —    | iTaiwan person/phone-centric links                                      |
| visit/willingness/history   |    ✓    |     △    | PropTech has viewing logs/questions/offers but local and buyer-centric  |
| supervisor/team filters     |    ✓    |     —    | iTaiwan confirmed                                                       |
| workspace/team permissions  |    ✓    |     —    | PropTech no team tenant model                                           |
| Loan / affordability        |    —    |     ✓    | iTaiwan official核心未發現                                                   |
| Holding cost                |    —    |     ✓    | PropTech deterministic                                                  |
| Tax screening               |    —    |     ✓    | PropTech TaxOracle                                                      |
| Terrain/hazard architecture |    ?    |     △    | iTaiwan official核心未發現；PropTech data not production-ready                |
| Evidence status/freshness   |    ?    |     ✓    | PropTech market/terrain emphasize unknown/unavailable semantics         |
| Decision summary            |    —    |     ✓    | deterministic viewing decision                                          |
| Case comparison             |    ?    |     ✓    | PropTech 2–3 saved cases                                                |
| Native LLM Copilot          |    —    |     —    | iTaiwan external Gemini；PropTech template-only                          |
| Multilingual UI             |    ?    |     ✓    | PropTech zh-TW/en/ja/ko runtime shell；live acceptance仍另議                |

---

# 8. Missing Capability Analysis

## A. iTaiwan 有、PropTech 完全沒有

1. 地號／建號作為正式搜尋入口。
2. 地址 → 土地 → 地上建物 → 門牌／建號的確認流程。
3. authorized cadastral parcel polygons 與 multi-parcel map workspace。
4. 土地 pin、分組、上色、透明度與 map state persistence。
5. 互動式基地 polygon、各邊長、面寬、路寬與 distance measurement。
6. 建物 master/list、floor filter、主建物／附屬面積與 full XLSX export。
7. 都市計畫、老屋年代與都更法定來源／進度 layers。
8. 現售房仲 listings、brand mix、current/previous asking price、降價與 supply clusters。
9. 土地／建物 title procurement、點數、status、personal/team dedupe history。
10. title document viewer、PDF、copy、share、map locate。
11. owner/landowner visits、willingness、contacts/address book。
12. workspace/team roles、supervisor view、personnel history與交接。

## B. iTaiwan 有、PropTech 有類似但較弱

| Domain        | PropTech 相似能力                                           | 為何較弱                                                          |
| ------------- | ------------------------------------------------------- | ------------------------------------------------------------- |
| Discovery     | address geocode、PLVR Property Finder                    | 找到的是歷史成交方向，不是可確認資產                                            |
| Map           | Map Insight / POI / terrain map                         | 是分析附屬畫面，不是所有 work objects 的 persistent canvas                 |
| Parcel        | user-upload GeoJSON/KML/SHP                             | 不是官方地籍；request-scoped；沒有 parcel number、multi-parcel editing   |
| Building      | PLVR building attributes、valuation inputs               | 是交易／輸入欄位，不是土地上的建物清單與 identity                                 |
| Zoning        | PLVR records may carry zoning                           | 沒有 source-versioned planning layer與適用法規脈絡                     |
| PLVR          | official market and valuation                           | PropTech 分析較深，但缺 parcel-centric map exploration               |
| CRM-ish       | case notes, due diligence, viewing logs/offers/timeline | buyer case workflow；無 owner/contact/team relationship history |
| Export        | HTML summary, browser print/PDF                         | 無 server artifact、XLSX dataset、team document lifecycle        |
| Collaboration | local saved cases                                       | 不是 multi-user，跨裝置也不可靠                                         |

## C. PropTech 有、iTaiwan 沒有或非官方核心

以下只表示 Gold Swagger 官方產品資料未把它們呈現為 iTaiwan 原生核心，不代表競品絕對沒有任何內部功能：

- explainable comparable-selection valuation、range、confidence 與 official-only transfer。
- loan / down-payment / monthly payment / income burden。
- total holding cost 與 affordability。
- TaxOracle deterministic eligibility／document screening。
- market freshness、coverage、sample sufficiency、unavailable/unknown trust states。
- terrain/disaster multi-provider architecture與 spatial intersection design；但 production data 仍不足。
- explicit Viewing Decision、missing-evidence next actions。
- 2–3 buyer cases comparison、decision report。
- evidence-aware reasoning 基礎與不把 unknown 當安全的產品原則。

## D. 兩邊都有但產品哲學不同

| 能力              | iTaiwan 哲學                            | PropTech 哲學                                    | VNext 應保留什麼                                                        |
| --------------- | ------------------------------------- | ---------------------------------------------- | ------------------------------------------------------------------ |
| PLVR            | 在 map/context 中查成交與分布                 | comparable → valuation → confidence → decision | 同一 facts 供 map exploration 與 decision pipeline                     |
| 地圖              | primary workspace 與 object continuity | location/risk evidence visualization           | 地圖成為 Professional canvas，Consumer 只在需要確認時出現                        |
| Property record | 土地／建物是持續工作的 anchor                    | Case 是分析輸出的 container                          | Property stable、Case task-specific，兩者分離                            |
| Notes/history   | 開發 CRM 與團隊接觸歷史                        | 買方 viewing/due-diligence notes                 | 統一 activity model，但用 case type/permissions 區分                      |
| Report/export   | 專業資料交付與 reuse                         | decision summary / compare                     | artifact 必須引用 entity + evidence version                            |
| AI              | 外部 Gemini 在已顯示資料後自由摘要                 | deterministic rule summary、尚無 LLM              | deterministic facts first；AI 有引用、scope、refusal與 human confirmation |

---

# 9. Competitive Advantages

## 9.1 iTaiwan 的真正優勢

1. **專業 workflow continuity**：query 不是終點，title、visit、team、export 都能接續。
2. **Property identity 先於正式付費動作**：先免費確認 address/building number，再調 title，降低錯標的與重複支出。[I-10]
3. **Map as workspace**：土地、建物、layers、measure、CRM、listings 共用同一空間 context。
4. **土地開發深度**：multi-parcel、old house、urban renewal、ownership/visits 對開發者有直接價值。
5. **Current market supply**：把 PLVR 與 active asking market 並置。
6. **Team memory**：contact/title/visit 不只留在個人手機或 Excel。

## 9.2 PropTech 的真正優勢

1. **Decision orientation**：不是讓使用者自己讀完十個 tab，而是回到「是否值得進一步看」。
2. **Explainable market reasoning**：official PLVR、comparable hierarchy、confidence、sample/freshness/coverage。
3. **Personal feasibility**：價格合理不等於買得起；loan/holding/tax 把資產資料連到家庭決策。
4. **Trust semantics**：unknown、unavailable、no data 不應自動轉成 safe/zero/low risk。
5. **可建立更好的 AI**：已有 deterministic calculations 與 evidence status，適合做 grounded synthesis，而不是讓模型直接猜法規與估值。

## 9.3 最重要的競爭洞察

不要把產品目標定成「iTaiwan but with AI」。iTaiwan 在 map-based professional data operations 上已形成連續工作流；PropTech 應吸收 identity 與 continuity，但把競爭面拉到 **evidence-backed decision intelligence**：同一標的的法定身分、官方資料、現售供給、風險、估價與資金是否互相一致，下一個可採取動作是什麼。

---

# 10. Features Worth Absorbing

## 第一層：必須成為平台骨架

1. **Property Identity Resolver + confirmation UI**：否則任何 parcel/building/title/listing 都可能掛錯。
2. **Durable Property/Case/Evidence persistence**：取代 localStorage-only，支援跨裝置與未來 team。
3. **Parcel/Building graph**：土地與建物 many-to-many，來源與 confidence 可追溯。
4. **Map-linked professional workspace**：但只在 Professional Mode 展開，不讓 Consumer 首頁變工具列表。
5. **Activity/Artifact history**：查詢、document、report、visit、export 都能回到 entity/case。

## 第二層：高價值專業能力

6. official/authorized parcel geometry、multi-parcel selection、color、measurement。
7. building list/floor filter/XLSX，並明示 coverage 與資料日期。
8. planning/zoning/urban-renewal/old-house context。
9. user-upload title/document + structured extraction + human confirmation。
10. current listing observations（先 user URL／partner feed，後續再擴來源）。
11. CRM contact/visit/willingness/team history，建立在 identity + tenant security 之後。

## 第三層：用 PropTech 哲學重做

12. PLVR + asking market discrepancy：成交 vs 開價、降價、供給與可能重複刊登。
13. title/planning/market/hazard conflict detection。
14. evidence brief：每個結論附來源、日期、coverage與缺件。
15. task-aware Copilot：Consumer 回答是否值得看；Professional 回答下一份資料、下一個 owner/contact/action。

---

# 11. Features Not Worth Copying

「不值得複製」不等於功能無用，而是目前不應成為 PropTech 的優先競爭點。

| 功能／做法                               | 不應直接複製原因                                                     | 可接受替代                                                                                |
| ----------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------------------------------ |
| 追求 15 品牌數量本身                        | 品牌數是 vanity metric；資料授權、去重與 freshness 才是產品價值                 | 先 1–2 partner feeds 或 user URL intake，證明 decision value                              |
| 大量主題 layer 堆疊                       | 容易讓首頁與 workspace 變工具目錄；使用者仍不知道先做什麼                           | 依 task 自動提出「需要的 3–5 個 layers」                                                        |
| 無任務目的的 parcel coloring              | 視覺酷，但沒有 candidate-site、owner outreach 或 compare context 時價值低 | color 對應 selection set/status/willingness                                            |
| 全面 hard-copy Windows local-shell UX | 限制 mobile/cross-device/team SaaS；PropTech 已是 web 架構          | responsive web + optional desktop utility only if required by source access          |
| 直接複製疑似工廠等 niche layers              | 對 consumer/核心 decision 非普遍；來源準確與法律含義不清                       | plugin/module later，明示 observation not fact                                          |
| 自建付費 title procurement 作為前三月主線      | upstream contract、個資、點數／退款、legal ops 都重                      | 先 private upload + parse + evidence linking                                          |
| 無 guardrail 的畫面型 Gemini             | 會把敏感 title 資料交給第三方，且容易生成法律／估價過度結論                            | consented, field-minimized, citation-bound AI；deterministic rules stay authoritative |
| 以功能數量取代 UX                          | 會破壞目前「幫我判斷這間房」的清楚定位                                          | Consumer/Professional shell 共用 backend，不共用資訊密度                                       |

---

# 12. Data Source Feasibility

## 12.1 可合法優先使用的官方來源

| Domain                     | 可能來源                                                                                                            | 可取得方式                                                   | Feasibility | 主要限制／判斷                                                                                             |
| -------------------------- | --------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- | :---------: | --------------------------------------------------------------------------------------------------- |
| PLVR                       | 內政部地政司 [本期實價登錄 batch](https://data.gov.tw/dataset/77051)                                                        | CSV/XML batch；政府資料開放授權第 1 版                             |      5      | 已是 repo 核心；1/11/21 發布節奏需 operator freshness                                                         |
| Government open data       | [政府資料開放授權條款 v1](https://data.gov.tw/license)                                                                    | dataset-specific download/API                           |      4      | 必須逐 dataset 核對 license、attribution、更新、欄位與再散布                                                        |
| Basemap/sections/land use  | [NLSC map services](https://maps.nlsc.gov.tw/pro/sysinfo.jsp)                                                   | 部分 WMS/WMTS/Web Map API 可免申請                            |      4      | 開放項目不代表 cadastral parcel vector 也開放                                                                 |
| Cadastral tiles/API        | [NLSC 介接服務說明](https://maps.nlsc.gov.tw/S09SOA/homePage.action)                                                  | 申請；公司可申請部分地籍圖磚／API                                      |     2–3     | WFS 等服務對象更受限；先取得書面核准與使用條件                                                                           |
| Address geocode            | [TGOS MAP API](https://api.tgos.tw/TGOS_MAP_API/docs/site/web/Application)                                      | account/key；Domain/IP validation                        |      4      | 進階 layers 可能需正式公文；provider SLA/limit需確認                                                             |
| Address ↔ parcel/building  | NLSC/TGOS/地籍便民服務、地方資料                                                                                           | API/application/partner                                 |      2      | 國家級完整 open master 未確認；[全國對照開放建議](https://data.gov.tw/suggests/136769) 本身反映需求缺口，不應假設有現成 open dataset |
| Building permit/use permit | 102 年後建管使用執照存根、地方 open data                                                                                     | 中央入口／地方 data                                            |      3      | 可補 permits，不等於 current canonical building-number master；地方欄位與品質不一致                                  |
| Planning/zoning            | NLSC/國土規劃圖台、地方都市計畫 open data                                                                                    | WMS/WMTS/WFS/ArcGIS REST/download                       |      3      | 法定版本、local coverage、都市／非都市土地規則需分開；不可把 visual tile 當 queryable law                                   |
| Urban renewal              | 地方更新處 datasets，例如 [臺北自行劃定更新單元](https://data.gov.tw/dataset/145802)                                              | local API/download/ArcGIS services                      |     2–3     | 全臺碎片化；8 類 mapping 需 legal source registry與版本                                                        |
| Transit                    | [TDX](https://tdx.transportdata.tw/about/service)                                                               | account/API key，依服務等級                                   |      4      | 認證、rate limit、terms與snapshot freshness；repo 現為 memory-only refresh                                  |
| Debris/landslide           | [ARDSWC Open Data API](https://data.ardswc.gov.tw/Data/OpenData/Api)                                            | public API/download                                     |     3–4     | 每個 layer 的 geometry/coverage/version需另確認；alert data ≠ long-term hazard polygon                      |
| Multi-hazard bundle        | [NCDR 2026 collection](https://datahub.ncdr.nat.gov.tw/dataset/detail?pid=d9793597-dcec-4a84-9bd9-e0f784669029) | application/download                                    |     1–2     | 官方標示限政府單位申請；不能把它當 commercial open API                                                               |
| Title transcripts          | [全國地政電子謄本](https://ep.land.nat.gov.tw/)                                                                         | authenticated/paid official service or licensed partner |     1–2     | 同意書禁止自動化程式擷取，且涉及個資；不應 screen scrape；可先 user upload                                                  |

## 12.2 需要 user upload／合作／付費授權

| Feature                                  | 建議取得模式                                                           | 原因                                                           |
| ---------------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------ |
| 正式 title PDF / encrypted artifact        | user upload；或簽正式地政／營運商／licensed partner contract                 | 不是 open data；身份、費用、個資與自動擷取限制                                 |
| Ownership/contact details                | user-provided + purpose/consent + role permissions               | 高敏感個資；不是可公開建立的 marketing database                            |
| Nationwide address↔parcel↔building graph | NLSC/TGOS/地方地政合作或 licensed resolver                              | public fragments 無法保證全臺 completeness                         |
| Active broker listings                   | partner feeds/API、publisher permission、user-provided listing URL | 跨站 aggregation 的 ToS、copyright、database rights、freshness 風險高 |
| Current building master                  | local government / land administration / partner datasets        | permit open data 不等於完整建號與現況 master                           |
| High-resolution hazard vectors           | agency agreement／licensed snapshots                              | public map view、MVT、政府限定 dataset不等於可重製向量                     |

## 12.3 不應做

- 不 scrape 全國地政電子謄本；官方同意書明確禁止 automated extraction，且要求遵守個資法。[電子謄本同意書](https://ep.land.nat.gov.tw/)
- 不逆向工程 iTaiwan private APIs、Windows local service 或資料庫。
- 不直接複製 iTaiwan 的 15-brand listing database、title history、urban-renewal mapping 或 CRM data。
- 不在未確認 publisher terms 時持續抓取、快照並再散布房仲圖片、文案、電話、price history。
- 不把 WMS/WMTS visual overlay 轉稱為 authoritative query result；需要 identify/query/feature license 與版本。
- 不因 data endpoint 在 browser 可見，就推論有商業再利用授權。

## 12.4 資料可行性對產品排序的影響

看起來最容易 demo 的「全品牌 listing map」與「一鍵調最新 title」其實是最難合法穩定營運的兩項。相反地，Property Identity confirmation UI、user-upload document、PLVR decision reasoning、multi-parcel interaction 可先用合法 inputs／已擁有資料建立產品價值。Roadmap 應先證明 workflow，再用合作擴 data breadth。

---

# 13. Property Identity Architecture

## 13.1 核心原則

輸入可以統一進入同一個 resolution pipeline，但不能假設每個輸入都唯一解析成一筆 Property：

```
address | lot number | building number | coordinate | map click | listing URL
  → normalize
  → call source-specific resolvers
  → produce candidates + relations + conflicts
  → show confirmation UI
  → user confirms intended subject
  → persist Property Entity Graph
```

地址、土地、建物與 listing 的真實關係常是 many-to-many。`PropertyEntity` 應被視為「已確認或正在確認的一組資產身分聚合」，而不是宣稱政府存在一個全國 universal property ID。

## 13.2 Resolution states

| State                | 語意                                       | 允許的後續動作                       |
| -------------------- | ---------------------------------------- | ----------------------------- |
| `received`           | 已收到 input                                | 無 substantive conclusion      |
| `normalizing`        | 地址／地號／建號格式化                              | 顯示 input only                 |
| `candidates_found`   | 有一或多個 candidates                         | map/list confirmation         |
| `ambiguous`          | 多筆或來源衝突                                  | 禁止自動綁 title/CRM；要求確認          |
| `confirmed`          | user/provider rule 明確確認 intended subject | 可建立 property/case links       |
| `partially_resolved` | 只知 point/address/parcel 其中一部分            | 可查 general context，結論明示限制     |
| `unresolved`         | 無可靠 candidate                            | 保留 input、提供人工查找，不捏造 identity  |
| `superseded`         | 地址重編、parcel split/merge、relation 更新      | 以 temporal edges 指向新 identity |

## 13.3 目前 repo 可 reuse 的部分

| Existing code                                           | 可 reuse                                                                          | 不可直接沿用的假設                                                   |
| ------------------------------------------------------- | -------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| `services/location_resolver.py`, map geocoding adapters | provider orchestration、normalized coordinates、source chain                       | mock result 不可成為 identity evidence；geocode point 不等於 parcel |
| `services/parcel_geometry.py`                           | secure upload parser、CRS normalize、topology repair、area、consistency、intersection | user geometry 不是 legal boundary；NLSC provider仍 disabled     |
| PLVR transaction/market/valuation                       | address/road/community hints、market evidence、comparable links                    | transaction row 不是 current building/parcel master           |
| `PropertyCaseDraft` / readiness                         | decision DTO、status language、compatibility adapter                               | 不能當 canonical property data model                           |
| `case-storage.ts`                                       | local migration source、safe compaction ideas                                     | 不可作 durable/team persistence                                |
| terrain evidence/status                                 | available/limited/unavailable/unknown semantics、source metadata                  | 未有 coverage proof的 provider不可升格 authoritative               |
| report/comparison components                            | rendering與 existing decision workflow                                            | report需改引用 stable entity/evidence versions                  |

## 13.4 要新增的 backend services

1. `PropertyResolutionService`：input normalization、provider fan-out、candidate ranking，不做無證據 merge。
2. `IdentityGraphRepository`：property、address、coordinate、parcel、building、listing relations 與 temporal validity。
3. `ParcelIdentityProvider`：NLSC/TGOS/partner；與 user geometry provider 分開。
4. `BuildingIdentityProvider`：land → above-ground buildings、address/building-number mapping、coverage metadata。
5. `ListingIntakeService`：URL allowlist/parser、publisher metadata、user confirmation；先不做 crawling platform。
6. `EvidenceRegistry`：每個 fact 的 source、retrieved/effective time、license、coverage、transformation lineage。
7. `ResolutionConflictService`：detect inconsistent address/point/parcel/building/listing。
8. `CaseCompatibilityService`：將現有 local saved case 匯入/映射到新 Case，不自動宣稱 resolved。

## 13.5 建議 API

| Method / endpoint                            | Purpose                                       | 核心 response／guard                                                         |
| -------------------------------------------- | --------------------------------------------- | ------------------------------------------------------------------------- |
| `POST /v1/property-resolutions`              | 接 address/lot/building/coords/map/listing URL | `resolution_id`, normalized input, candidates, sources, conflicts, status |
| `GET /v1/property-resolutions/{id}`          | poll async providers                          | status + candidate changes；無 raw secrets                                  |
| `POST /v1/property-resolutions/{id}/confirm` | human selects parcel/building/listing set     | idempotent confirmation、actor、time、evidence refs                          |
| `POST /v1/property-resolutions/{id}/reject`  | 明示不是這些 candidates                             | 保存 feedback，不靜默換 candidate                                                |
| `GET /v1/properties/{property_id}`           | property summary                              | typed links + freshness/coverage                                          |
| `GET /v1/properties/{id}/graph`              | Professional graph                            | permissions filter sensitive nodes                                        |
| `GET /v1/properties/{id}/evidence`           | evidence ledger                               | fact/source/effective/retrieved/license/status                            |
| `POST /v1/cases`                             | 建立 consumer/pro case                          | requires workspace、purpose、property relation可 pending                     |
| `POST /v1/cases/{id}/attach-resolution`      | 將 confirmed resolution 綁 case                 | explicit, auditable                                                       |

所有 mutation 需 `Idempotency-Key`、actor/workspace context 與 audit event；provider errors 回 structured status，不回 200 + fake data。

## 13.6 前端入口

首頁只保留兩個 primary tasks：

- **分析一個物件**：Consumer default。
- **開啟專業研究工作台**：Professional。

兩者共用一個 omnibox，接受地址、地號、建號、座標、map click、房仲 URL。解析後先顯示 compact confirmation sheet：map point、parcel candidates、building candidates、source/freshness、衝突與「目前只定位到點位」提醒。只有 Professional Mode 展示完整 graph inspector。

---

# 14. Parcel / Building / Listing Entity Model

## 14.1 建議 graph

```
flowchart TD
  PE["Property Entity"] --> A["Address"]
  PE --> P["Parcel"]
  PE --> B["Building"]
  PE --> L["Listing"]
  PE --> C["Case"]
  P <--> B
  L --> LO["Listing Observation"]
  C --> E["Evidence / Artifact / Activity"]
```

圖中的線不是無來源的 foreign key 猜測，而是 `property_relations`：relation type、source、confidence、valid\_from/to、confirmed\_by、confirmation\_time、evidence\_id 都必須保存。

## 14.2 Core models

| Model                  | 重要欄位                                                                                                       | 設計說明                                                                 |
| ---------------------- | ---------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| `workspaces`           | id, name, type, retention\_policy                                                                          | Consumer 可有 personal workspace；Pro 為 team workspace                  |
| `workspace_members`    | workspace\_id, user\_id, role, status                                                                      | owner/admin/manager/member/viewer；離隊不刪歷史 actor                       |
| `property_entities`    | id, resolution\_status, display\_label, centroid, created\_from                                            | aggregate root，不宣稱官方 universal ID                                    |
| `addresses`            | normalized/canonical text, admin codes, coordinates, source, valid time                                    | 原始 input另保存但不當 canonical fact                                        |
| `parcels`              | county/district/land-office/section/subsection/lot main/sub, geometry ref, legal\_boundary, source version | natural key需 local authority context；geometry可 temporal              |
| `buildings`            | authority context, building no main/sub, completion date, floors, areas, source                            | 不能只以門牌 unique                                                        |
| `listings`             | publisher, external\_id/url hash, subject type, status                                                     | source record；不要把 URL 當 property ID                                  |
| `listing_observations` | listing\_id, observed\_at, asking price, unit price, status, content hashes                                | price change與freshness；原始素材需依 license retention                      |
| `property_relations`   | from/to, type, confidence, source, temporal validity, confirmed\_by                                        | typed many-to-many edges                                             |
| `cases`                | workspace, case\_type, purpose, status, primary\_property\_id, owner                                       | task/workflow container；buy\_due\_diligence, development, brokerage等 |
| `evidence_items`       | subject, fact\_type, value/ref, source\_id, effective/retrieved, coverage, quality, license                | append/version，derived fact有 lineage                                 |
| `artifacts`            | case/property, type, storage object, version, checksum, source                                             | reports/title/XLSX；private by default                                |
| `activities`           | case/property/contact, type, actor, occurred\_at, payload schema version                                   | note/visit/query/export/share/task history                           |

## 14.3 Sensitive models

`documents`, `parties`, `contacts`, `ownership_interests`, `encumbrances` 必須放在更嚴格的 private schema／tables；UI 按 purpose與role最小揭露。所有權資料應記 document evidence 與 effective date，不把過期 transcript 當 current truth。不要把 contact、電話、owner names塞在 generic JSONB case payload。

## 14.4 Postgres / Supabase implementation guidance

- normalized relational core；source-specific raw/parsed snapshots才用 JSONB，且不直接 expose。
- PostGIS `geometry` 用於 authoritative boundaries與spatial joins，`geography`/point用於距離；GiST indexes。
- normalized lot/building keys、publisher external IDs、case/workspace foreign keys建立 composite/partial indexes。
- exposed schema 所有 tenant rows 強制 RLS；policy filter columns需 index；views使用 `security_invoker` 或 server-only private schema。
- Supabase Storage private bucket保存 title/document/report；signed URL 短期分享；禁止 public title bucket。
- `service_role` 只在 backend/provider jobs；frontend 使用 user JWT 與 least privilege。
- audit log append-only；document download/share/export 都產生 activity。

## 14.5 Identity merge / split

禁止用模糊地址一次性 `UPDATE property_id` 合併所有資料。正確流程：create merge proposal → compare parcel/building/listing evidence → human confirm → add `same_as`/`supersedes` relation → migrate only approved case links → keep original nodes and audit. Parcel split/merge、門牌整編與listing relist都需要 temporal history。

---

# 15. Professional Workspace Architecture

## 15.1 Workspace 不是 16 個首頁按鈕

Professional Mode 的 primary structure 應以工作任務呈現：

1. **確認標的**：Identity, Parcel, Building。
2. **理解可利用性**：GIS, Planning, Redevelopment, Title。
3. **理解市場與風險**：PLVR, Listings, Terrain/Hazard, Valuation。
4. **判斷資金與成本**：Finance, Tax。
5. **推進案件**：CRM, Collaboration, Tasks, Artifacts。
6. **取得結論**：AI Copilot, Decision, Report。

模組仍存在，但 navigation 應隨 case purpose 排序。例如 brokerage acquisition 先 current listings/CRM；development case 先 parcel aggregation/planning/title；consumer buy case 先 identity/market/risk/finance。

## 15.2 建議畫面結構

| 區域                | 內容                                                                   | UX 原則                               |
| ----------------- | -------------------------------------------------------------------- | ----------------------------------- |
| Context header    | confirmed identity、address、parcel/building chips、status、last refresh | 永遠看得到「現在研究的是誰」                      |
| Map canvas        | parcel/building/listing/layer/measure/visit                          | Pro only 可長時間操作；selection與table雙向同步 |
| Evidence rail     | source/status/freshness/coverage/conflicts                           | 點任何結論可回 evidence                    |
| Task panel        | current objective、missing evidence、next actions、assigned owner       | 防止工具漫遊                              |
| Module detail     | Parcel/Planning/Market/...                                           | lazy load，保留 context                |
| Copilot panel     | ask about selected property/case/evidence                            | 不自動讀未授權敏感文件；回答含引用與scope             |
| Activity timeline | query/title/upload/visit/share/report/decision                       | 可過濾 personal/team/system            |

## 15.3 Backend module boundaries

```
Identity service
  → Property graph
  → Evidence registry
       ↘ Parcel/Building/Planning providers
       ↘ PLVR/Listing providers
       ↘ Terrain/Location providers
       ↘ Document/Title pipeline
       ↘ Finance/Tax calculators
  → Case workflow + Activity/CRM
  → Synthesis service
  → Artifact/report service
```

Provider acquisition、deterministic calculators、AI synthesis必須分開。AI 不直接操作 provider raw responses或寫 authoritative fields；它只能讀 approved evidence DTO，寫 `analysis_draft`，再由 human/system rules promote。

---

# 16. Consumer vs Professional Mode

## 16.1 合理，但不能 fork backend

| Dimension   | Consumer Mode                           | Professional Mode                                            | Shared core                        |
| ----------- | --------------------------------------- | ------------------------------------------------------------ | ---------------------------------- |
| Job         | 幫我判斷這間房是否值得進一步看                         | 研究土地／建物／基地／案件並推進工作                                           | Property graph + Case + Evidence   |
| Intake      | address / listing URL / map point       | 全部 input + parcel/building identifiers                       | Resolution API                     |
| Identity UI | 只顯示少量 candidates與必要確認                   | graph inspector、multi-select、conflict tools                  | same resolution state              |
| Map         | confirmation、關鍵風險與周邊                    | persistent workspace、layers、measure、CRM                      | same spatial facts                 |
| Modules     | task-progressive，預設 market/risk/finance | purpose-based full modules                                   | same services/read models          |
| Case        | personal buy case                       | team case types, assignment, tasks                           | same `cases` table with case\_type |
| Documents   | upload/checklist，最小敏感顯示                 | title/document lifecycle與team permissions                    | same private artifact model        |
| AI          | 短結論、缺件、看房問題、下一步                         | discrepancy analysis、document brief、owner/market/action plan | same evidence-bound synthesis      |
| Export      | concise decision report                 | configurable evidence pack/XLSX/PDF                          | same artifact/version service      |

## 16.2 Compatibility with current Property Case

現有 `SavedCase` 應先成為 `legacy_case_snapshot`：

1. 使用者登入後可選擇匯入 local cases。
2. 只建立 Case 與 raw input snapshot，不自動宣稱 property resolved。
3. 若只有 address，啟動 resolution confirmation。
4. valuation/market/terrain compact snapshots映射到 versioned evidence references；無 provenance者標 `legacy_unverified`。
5. 保留 existing compare/report UI adapter，逐步改讀新 API DTO。

這讓兩個 modes 共用 backend，又避免一次 rewrite 破壞 production behavior。

---

# 17. AI Enhancement Opportunities

## 17.1 可以明顯超越 iTaiwan 的 AI

| Opportunity                    | Input                                            | Output                                             | 為何比外部 Gemini 更好                                                  |
| ------------------------------ | ------------------------------------------------ | -------------------------------------------------- | ---------------------------------------------------------------- |
| Identity discrepancy detection | address/point/parcel/building/listing candidates | conflicts + questions + confidence                 | 在正式分析前阻擋掛錯標的                                                     |
| Evidence brief                 | approved evidence DTOs                           | cited facts, unknowns, next evidence               | 每句可追 source/version，不只讀螢幕                                        |
| Comparable explanation         | PLVR comps + subject conditions                  | why included/excluded, sensitivity                 | deterministic valuation仍 authoritative，AI負責解釋                    |
| Asking vs sold analysis        | listing observations + PLVR                      | premium, price cuts, supply, duplicate caveat      | 把 current supply 與成交基礎接到 decision                                |
| Title reading assistant        | user-authorized parsed document                  | owner/encumbrance summary, red flags, questions    | field-minimized、document citations、no unsourced legal conclusion |
| Planning conflict assistant    | zoning/plan/renewal evidence                     | applicable layers, conflicts, professional checks  | 法定版本與coverage可見                                                  |
| Risk-finance synthesis         | hazard/location/valuation/loan/holding/tax       | scenario-specific decision memo                    | 不是 generic map data summary                                      |
| Missing-data planner           | case purpose + evidence statuses                 | ranked acquisition plan                            | 不把 unknown 當 safe；直接驅動 workflow                                  |
| CRM briefing                   | authorized activities/contacts/tasks             | next-call brief, stale follow-ups, handoff summary | 讀 team history而非單一畫面                                             |
| Report drafting                | confirmed decisions + evidence                   | consumer/professional artifacts                    | artifact version、citations與approval trail                        |

## 17.2 AI workflow

```
User question / system task
  → Permission and purpose check
  → Evidence retrieval by property + case + time
  → Deterministic facts/calculations
  → Conflict / missing-data gate
  → LLM draft with inline evidence IDs
  → claim validator
  → human confirmation for legal/title/CRM actions
  → versioned analysis artifact
```

## 17.3 AI 不應做

- 不由模型生成 parcel/building identity 或自動 merge graph。
- 不由模型重算 loan/tax/valuation authoritative numbers。
- 不把未命中 hazard 解釋為無風險。
- 不在未經 consent 時把 title、owner/contact資料送外部 model。
- 不根據 public listing文案推測 owner identity。
- 不生成「一定可都更」「一定可貸」「一定值得買」等結論。
- 不自動對外寄信、聯絡 owner、購買 title或分享文件；需要明確 user action與recipient verification。

## 17.4 現有 AI code 的演進方式

保留 `risk-summary.ts` 與 calculators 做 deterministic foundation；將 `llm_service.py` 從 template-only 升級為獨立 `SynthesisService`，但要等 Evidence DTO、prompt contract、citation validation、PII redaction、evaluation set 與 provider observability完成。產品不可在此之前宣稱 native AI decision copilot 已上線。

---

# 18. CRM / Team Workflow

## 18.1 建議 end-to-end workflow

```
Confirmed parcel/building
  → create acquisition/development case
  → add party/contact only with lawful purpose
  → record visit/call/note + willingness + role
  → link contact to parcel/building/case with provenance
  → create task / next follow-up / owner
  → manager sees map + pipeline + stale cases
  → team member opens history before contact/title purchase
  → handoff preserves actor and timeline
  → export minimum necessary report
```

## 18.2 Models and permissions

| Model                    | Key relationships                                    | Privacy rule                                   |
| ------------------------ | ---------------------------------------------------- | ---------------------------------------------- |
| `parties`                | ownership/legal role; document-derived               | 最敏感，僅 authorized case roles                    |
| `contacts`               | person/org/phone/email, source, consent/lawful basis | phone search不對全 workspace預設開放                  |
| `contact_property_links` | contact ↔ parcel/building/case, role, confidence     | 不把未確認聯絡人當 owner                                |
| `visits`                 | subject, contact, actor, method, willingness, notes  | notes field audit + retention；export redaction |
| `tasks`                  | case, assignee, due date, status, dependency         | manager可看工作，不必看所有敏感內容                          |
| `teams` / `members`      | roles, active/left status                            | 離隊保留 actor display，立即撤存取                       |
| `shares`                 | artifact/record, recipient workspace, scope, expiry  | 可撤銷、可稽核、最小範圍                                   |

## 18.3 不要做成通用 CRM

CRM 的 anchor 必須是 confirmed property/case，而不是先做無邊界的 customer database。MVP 只做 visit、willingness、contact role、next task、team history與map filter；marketing automation、mass messaging、lead scoring、commission accounting不是早期範圍。

---

# 19. Proposed VNext Architecture

## 19.1 推翻線性「資料全查完才判斷」

所有 module 依序查完會慢、昂貴且不符合不同角色。VNext 應先確認 identity，再依 case purpose 建立 evidence plan，並行取得需要的資料：

```
flowchart TD
  I["Intake"] --> R["Resolve candidates"]
  R --> H["Human confirmation"]
  H --> G["Property + Case Graph"]
  G --> Q["Task Evidence Plan"]
  Q --> E["Evidence Acquisition Lanes"]
  E --> V["Quality / Conflict Gate"]
  V --> S["Reasoning + Synthesis"]
  S --> A["Decision / Action / Artifact"]
```

Evidence acquisition lanes：

- **Physical/legal**：parcel、building、planning、redevelopment、title/document。
- **Market**：PLVR、comparables、listing observations、supply。
- **Context/risk**：location、transit、terrain、hazard。
- **Finance/tax**：valuation、loan、holding cost、tax screening。
- **Work history**：case、contacts、visits、tasks、team artifacts。

## 19.2 Architecture layers

| Layer                      | Responsibility                             | Non-responsibility       |
| -------------------------- | ------------------------------------------ | ------------------------ |
| Intake                     | accept six input types, detect intent      | 不做 property conclusion   |
| Resolution                 | candidates/conflicts/confirmation          | 不把 geocode當 parcel       |
| Entity graph               | stable typed identity + temporal links     | 不存所有 source raw payload  |
| Provider layer             | lawful acquisition, source adapters, jobs  | 不決定購買建議                  |
| Evidence layer             | version/provenance/coverage/status/lineage | 不把 unavailable轉成 no-risk |
| Deterministic intelligence | valuation/finance/tax/spatial calculations | 不產生自由法律建議                |
| AI synthesis               | explain, compare, plan, draft              | 不改 authoritative facts   |
| Case workflow              | task state, activities, CRM, approvals     | 不複製 property facts       |
| Artifact layer             | report/XLSX/PDF/share/version              | 不公開敏感文件                  |
| UX shells                  | Consumer or Professional presentation      | 不 fork domain logic      |

## 19.3 Event sequence for a property change

當 parcel/building source更新或 listing觀察變化時：create new evidence version → mark dependent analyses stale → recompute deterministic derived facts → notify case owners only if impact threshold met → AI draft change summary → human reviews material decision change。舊 report不覆寫，標示 based-on version。

---

# 20. Development Priority Matrix

## 20.1 評分規則

所有維度 1–5。正向項目越高越好；負擔項目越高代表越困難／風險越高：

- `UV` User value；`CV` Competitive value；`TD` Technical difficulty；`DA` Data availability。
- `AL` API/licensing difficulty；`LR` Legal/ToS risk；`MC` Maintenance cost。
- `AI` AI enhancement potential；`Demo` competition demo value；`LTV` long-term commercial value。

`Feasibility = 6 − average(TD, AL, LR, MC)`
`Priority Score = 20 × (0.20 UV + 0.12 CV + 0.08 DA + 0.10 AI + 0.08 Demo + 0.12 LTV + 0.30 Feasibility)`
表中分數四捨五入至整數（`.5` 向上）。
Score 是比較工具，不會凌駕 dependency/security gate；例如 title upload score高，但仍依賴 durable case/artifact permissions。

| Feature                                |  UV |  CV |  TD |  DA |  AL |  LR |  MC |  AI | Demo | LTV | Score /100 | 建議                             |
| -------------------------------------- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :--: | :-: | ---------: | ------------------------------ |
| User title upload + structured parse   |  5  |  5  |  3  |  5  |  2  |  3  |  4  |  5  |   5  |  5  |     **88** | P1 after identity/security     |
| Evidence-bound AI brief                |  5  |  5  |  4  |  5  |  2  |  3  |  4  |  5  |   5  |  5  |     **87** | P1 differentiator              |
| Durable Case / Evidence graph          |  5  |  5  |  4  |  5  |  2  |  2  |  4  |  5  |   4  |  5  |     **86** | P0 foundation                  |
| Property Identity Resolver             |  5  |  5  |  4  |  3  |  4  |  2  |  3  |  5  |   5  |  5  |     **83** | P0 foundation                  |
| Property-linked CRM                    |  5  |  5  |  4  |  5  |  2  |  4  |  4  |  5  |   4  |  5  |     **83** | P2 after tenant/privacy        |
| Listing URL intake + observations      |  4  |  4  |  3  |  5  |  2  |  2  |  3  |  5  |   5  |  4  |     **82** | P1; user/partner source        |
| Official/multi-parcel GIS workspace    |  5  |  5  |  4  |  3  |  4  |  2  |  4  |  4  |   5  |  5  |     **80** | P1; NLSC contract gate         |
| Team collaboration + history           |  5  |  5  |  4  |  5  |  2  |  4  |  4  |  3  |   4  |  5  |     **79** | P1/P2 foundation for pro       |
| PDF/XLSX artifact service              |  4  |  3  |  2  |  5  |  1  |  2  |  2  |  3  |   4  |  4  |     **79** | Quick win after durable models |
| Planning/zoning layers                 |  4  |  4  |  3  |  3  |  3  |  2  |  4  |  4  |   4  |  4  |     **72** | Local pilots first             |
| Urban-renewal + old-house intelligence |  4  |  4  |  3  |  2  |  3  |  2  |  4  |  4  |   5  |  4  |     **72** | P2; source registry required   |
| Building master/list/XLSX              |  4  |  4  |  4  |  2  |  4  |  2  |  4  |  4  |   4  |  5  |     **70** | P1/P2; coverage hard           |
| Cross-brand listing aggregation        |  5  |  5  |  5  |  1  |  5  |  5  |  5  |  4  |   5  |  5  |     **68** | Partner-only; no scraping      |
| Direct title procurement               |  5  |  5  |  5  |  1  |  5  |  5  |  5  |  4  |   4  |  5  |     **66** | Later strategic partnership    |
| Niche/suspected-factory layers         |  2  |  2  |  3  |  2  |  3  |  3  |  4  |  2  |   3  |  2  |     **46** | Defer/plugin only              |

## 20.2 未來三個月建議的五項

依 dependency 而不是單看 score，前三個月應是：

1. **Property Identity Resolver + confirmation UI**：先支援 address、coords、map click、manual lot/building input；provider不可用時保留 partial resolution。
2. **Durable Property/Case/Evidence foundation**：server persistence、auth/workspace、RLS、local case import bridge。
3. **Multi-parcel GIS workspace MVP**：user upload + authorized/open layers；selection/color/area/edge/distance；官方 parcel service取得授權後才升級。
4. **Listing URL intake + observation snapshots**：不做跨站 scraping；讓 user確認 listing與building/parcel relation，接 PLVR asking-vs-sold。
5. **Evidence Brief MVP**：先覆蓋 existing PLVR/valuation/location/terrain status/loan/holding/tax + new identity evidence；每句有 evidence ID與unknown。

Building/planning 與 title upload 可在第五項的下一個 slice 進入；若 competition demo偏土地開發，可將 listing URL intake換成「building candidates + local planning pilot」，但不能同時承諾 nationwide completeness。

---

# 21. Kiro Stage Roadmap

## 21.0 執行規則

- 每一 Stage 一個 isolated branch/worktree 與明確 migration boundary；不得在同一關順手重構不相關 production code。
- 先保留現有 Consumer journey；新架構以 feature flag／compatibility adapter 漸進接入。
- 每關交付 code、migration、API contract、tests、data provenance、operator runbook 與 acceptance evidence；未達 gate 停止，不進下一關。
- 所有 external provider 需 fake/contract tests + sandbox/real-provider acceptance分開；fixture通過不得宣稱 production provider通過。
- schema migration只 forward migration；先 dry-run/backup/rollback plan。不得改寫或清除現有 PLVR production tables。
- 每關最後至少跑 frontend typecheck/lint/build、backend tests、migration tests、API contract tests與 targeted E2E；警告與未跑項目明列。

## Stage 0 — Architecture Preparation

| 項目                  | 規格                                                                                                                                |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Objective           | 固定 domain boundaries、security/tenant model、evidence contract與migration strategy，不增加使用者功能。                                         |
| Scope               | ADRs、OpenAPI skeleton、schema ERD、provider registry、status taxonomy、feature flags、legacy case migration plan、data-source register。 |
| Backend             | 定義 modules/interfaces；建立 server-only config boundary、structured error、idempotency與audit event contract。                           |
| Frontend            | 定義 Consumer/Professional route/shell contracts與identity confirmation wire contract；不改首頁行為。                                        |
| Data                | inventory現有 PLVR/market/pilot/tax schemas；確認 private/exposed schemas、backup與retention。                                            |
| New models          | 僅 schema/DTO proposals：workspace, property, relation, case, evidence, artifact, activity。是否建立空表由migration review決定。               |
| API                 | `/v1` naming/error/status conventions；無 public feature endpoints。                                                                 |
| Tests               | architecture/static guards、OpenAPI snapshot、migration dry-run、RLS policy test plan、legacy compatibility fixtures。                 |
| Acceptance criteria | ADR核准；零 production behavior差異；現有 build/tests保持；每個 sensitive table有access matrix；資料來源有license owner。                               |
| Dependencies        | repo clean baseline；Supabase/Postgres owner decisions；NLSC/TGOS application owner。                                                |
| Risk                | 過早建模或generic abstraction；RLS只寫文檔未測。                                                                                               |
| 不應碰                 | PLVR logic、valuation formulas、terrain claims、deployment secrets、UI redesign、provider scraping。                                    |

## Stage 1 — Property Identity + Durable Case Foundation

| 項目                  | 規格                                                                                                                               |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| Objective           | 六種 input 進同一 resolution flow，human-confirm後建立 stable property/case links。                                                        |
| Scope               | address/coords/map click/manual lot/manual building/listing URL intake；candidate/ambiguous/confirmed；local case import bridge。   |
| Backend             | `PropertyResolutionService`、graph repository、conflict service、workspace auth；async provider job interface。                       |
| Frontend            | omnibox、candidate confirmation sheet、partial/unresolved states；Consumer default，Professional link only。                          |
| Data                | TGOS/現有 location resolver；manual parcel/building identifiers；listing URL user input；禁止 mock promote。                             |
| New models          | workspaces, members, property\_entities, addresses, geo\_references, property\_relations, cases, evidence\_items, audit\_events。 |
| API                 | `POST/GET /v1/property-resolutions`; confirm/reject; `GET /v1/properties/{id}`; `POST /v1/cases`; attach resolution。             |
| Tests               | normalization、duplicate inputs、multiple candidates、provider timeout、mock rejection、RLS cross-tenant、idempotency、legacy import。   |
| Acceptance criteria | 不確認就不綁 title/listing/CRM；同 input重送不重複建 graph；cross-workspace不可讀；existing journey仍可運作。                                            |
| Dependencies        | Stage 0；Auth/workspace decision；provider terms。                                                                                  |
| Risk                | address false merge、tenant leak、把 geocode當 parcel、legacy snapshots失去 provenance。                                                 |
| 不應碰                 | official cadastral claims、automatic entity merge、AI synthesis、full CRM、existing valuation math。                                  |

## Stage 2 — Parcel / GIS

| 項目                  | 規格                                                                                                                                  |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| Objective           | 提供可追溯的 parcel workspace，清楚區分 official、user-provided與point reference。                                                                |
| Scope               | parcel candidates、geometry view、multi-select/color、polygon/line measurement、area/edges/distance、upload、spatial consistency。         |
| Backend             | reuse secure parser/CRS/topology/intersection；new parcel provider registry、geometry versioning、PostGIS queries。                     |
| Frontend            | map/table sync、selection sets、layer legend、legal-boundary badge、measurement disclaimer與save-to-case。                                |
| Data                | NLSC approved services/open basemaps；user GeoJSON/KML/SHP；LANDSECT context。                                                         |
| New models          | parcels, parcel\_geometries, geometry\_versions, site\_selections, measurements, map\_styles。                                       |
| API                 | property parcels/geometry；upload/confirm；site selections；measurements；spatial analysis。                                             |
| Tests               | CRS 3825/3826/4326、invalid ZIP/path traversal、large file、topology repair、area tolerances、multi-parcel、official/user precedence、RLS。 |
| Acceptance criteria | point radius絕不畫成 parcel boundary；source/version visible；upload不對第三方傳送；measurement不稱法定成果。                                            |
| Dependencies        | Stage 1；PostGIS；NLSC authorization decision。                                                                                        |
| Risk                | legal boundary misrepresentation、geometry performance、provider quota、CRS error。                                                     |
| 不應碰                 | cadastral WFS without permission、survey/legal certification、hazard「無風險」結論、automatic ownership links。                                |

## Stage 3 — Building / Planning / Redevelopment

| 項目                  | 規格                                                                                                                                          |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| Objective           | 從 confirmed parcel 找候選建物，並加入可版本化的 planning context。                                                                                         |
| Scope               | land→building candidates、address/building number confirmation、floors/areas/age、XLSX；zoning/planning/old-house/urban-renewal local pilot。    |
| Backend             | building provider、parcel-building link、planning evidence registry、jurisdiction/version resolver。                                            |
| Frontend            | building list/floor filter、identity conflicts、planning layer groups、applicability/coverage panel、XLSX export。                               |
| Data                | building/use-permit open data與partner sources；NLSC/local planning/urban-renewal datasets。                                                   |
| New models          | buildings, building\_addresses, parcel\_building\_relations, planning\_areas, planning\_rules, redevelopment\_cases。                        |
| API                 | property buildings；confirm building；planning evidence/layers；building export jobs。                                                          |
| Tests               | one parcel-many buildings、one building-many parcels、address changes、local coverage missing、plan version changes、XLSX unfiltered export、RLS。 |
| Acceptance criteria | building candidate不是canonical直到confirm；planning source/effective date visible；pilot外顯示not covered，不顯示空白安全。                                  |
| Dependencies        | Stages 1–2；選定1–2 pilot jurisdictions；data license mapping。                                                                                  |
| Risk                | nationwide data inconsistency、法規版本誤用、permit≠current building master。                                                                        |
| 不應碰                 | 宣稱全臺building completeness、automatic development rights、容積／都更通過保證。                                                                           |

## Stage 4 — Market / Listings

| 項目                  | 規格                                                                                                                                                     |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Objective           | 把已成熟的 PLVR decision pipeline掛到 confirmed property，加入合法 current asking observations。                                                                    |
| Scope               | parcel/building-centric PLVR radius/context、existing valuation/comparables；user listing URL/partner feeds、price observation、possible duplicate caveat。 |
| Backend             | reuse PLVR read models；listing intake/observation/dedupe candidate service；staleness jobs。                                                             |
| Frontend            | sold vs asking、price change、supply context、source link、duplicate review、map/list toggle。                                                               |
| Data                | official PLVR；user URLs；signed partner feeds。沒有授權就不做跨品牌 crawler。                                                                                       |
| New models          | listings, listing\_observations, listing\_property\_candidates, publisher\_sources, source\_terms。                                                     |
| API                 | property market/comparables/valuation；listing intake/observe/link/reject；supply summary。                                                               |
| Tests               | PLVR freshness/coverage、listing relist、price change、same URL duplicate、possible duplicate not identity、publisher removal/retention、ToS allowlist。      |
| Acceptance criteria | Property Finder仍明示historical, not active listing；每筆 listing有publisher/as-of；possible duplicate需人工confirm；來源撤回可停止與清理。                                   |
| Dependencies        | Stage 1；部分Stage 3 building identity；legal review/partner。                                                                                              |
| Risk                | scraping/redistribution、stale listings、false duplicate、copyright images/content。                                                                       |
| 不應碰                 | 未授權15-brand aggregation、暗中抓取、copy competitor data、讓asking price污染official valuation。                                                                   |

## Stage 5 — Title / Documents

| 項目                  | 規格                                                                                                                                         |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Objective           | 先用安全的 user document workflow建立 title intelligence；直連採購另設 commercial gate。                                                                  |
| Scope               | upload、virus/type/size checks、private storage、OCR/parse、page/field citations、human confirmation、document reuse/history、PDF access。         |
| Backend             | document ingestion queue、parser、PII classifier、artifact service、permission/share/audit；optional procurement interface only。                |
| Frontend            | upload consent、viewer、field citations、owner/encumbrance draft、redaction/share/expiry、locate to property。                                   |
| Data                | user-authorized title/document；正式 procurement需 partner contract；不得 scrape電子謄本。                                                             |
| New models          | documents, document\_versions, parsed\_facts, parties, ownership\_interests, encumbrances, shares, access\_events。                         |
| API                 | document upload/status/view/parsed-facts/confirm/redact/share；procurement endpoint保持disabled直到contract gate。                               |
| Tests               | malware/zip bomb/type spoof、OCR failure、PII/RLS、signed URL expiry、cross-tenant、page citation、stale transcript、deletion/retention。          |
| Acceptance criteria | private-by-default；未確認 parsed fact不成authoritative evidence；每個 ownership claim連document/page/as-of；下載分享可稽核。                                 |
| Dependencies        | Stage 1 security/artifacts；Stage 3 building/parcel identity；privacy/legal review。                                                          |
| Risk                | 個資外洩、過期title當current、OCR hallucination、third-party model data transfer。                                                                    |
| 不應碰                 | automated official-site extraction、public bucket、owner marketing database、AI legal verdict、direct purchase without refund/contract design。 |

## Stage 6 — CRM / Collaboration

| 項目                  | 規格                                                                                                                  |
| ------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Objective           | 讓 property-linked工作歷史可累積、交接與管理，而不做無邊界通用CRM。                                                                         |
| Scope               | contacts/roles、visits、willingness、notes、tasks、team filters、map points、handoff、artifact reuse。                       |
| Backend             | activity service、contact dedupe candidates、task/pipeline、role policies、retention/export/deletion。                   |
| Frontend            | case timeline、visit form、address book、map filter、manager workload/stale follow-up、handoff view。                     |
| Data                | user/team-entered；document-derived party需明確source與權限；不買來源不明名單。                                                      |
| New models          | contacts, contact\_methods, contact\_property\_links, visits, tasks, assignments, pipelines, handoffs。              |
| API                 | CRUD with versioning；timeline；map query；team filters；task transitions；handoff；minimum export。                       |
| Tests               | role matrix、leaving member、contact false merge、concurrent edits、audit immutability、PII export/deletion、map privacy。 |
| Acceptance criteria | manager可看進度但未必看敏感content；team查看history可避免重複接觸；離隊即撤access但actor history保留。                                           |
| Dependencies        | Stages 1 and 5 privacy model；Stage 2 map optional。                                                                  |
| Risk                | 個資法、內部濫用、notes過度揭露、contact merge錯誤、scope creep。                                                                     |
| 不應碰                 | bulk marketing、automatic outreach、commission/ERP、owner lead resale、未驗證contact=owner。                                |

## Stage 7 — AI Intelligence

| 項目                  | 規格                                                                                                                                                           |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Objective           | 在 deterministic facts與evidence registry上提供可引用、可拒答、可評估的 synthesis。                                                                                            |
| Scope               | identity conflicts、evidence brief、asking-vs-sold、title summary、missing-evidence plan、consumer/pro report draft。                                              |
| Backend             | retrieval policy、approved Evidence DTO、PII redaction、model gateway、prompt/version registry、claim validator、eval/telemetry。                                   |
| Frontend            | cited answer、fact/interpretation separation、unknowns、refresh/stale badge、approve/edit、feedback。                                                              |
| Data                | only authorized evidence；synthetic/redacted eval set；model provider DPA/retention config。                                                                    |
| New models          | analysis\_runs, model\_configs, prompt\_versions, citations, claim\_checks, user\_feedback。                                                                  |
| API                 | analysis create/status/result/approve；case/property brief；comparison；feedback。                                                                               |
| Tests               | gold-set factuality、citation coverage、unknown preservation、prompt injection in documents/listings、PII leakage、deterministic number consistency、latency/cost。 |
| Acceptance criteria | 100% material claims有evidence或標示inference；calculations與source facts不可被模型改寫；high-risk legal/tax/title claims需review。                                          |
| Dependencies        | Evidence layer + sufficient Stages 1–6 slices；privacy/model vendor approval。                                                                                 |
| Risk                | hallucination、automation bias、敏感資料外流、cost/latency、stale analysis。                                                                                            |
| 不應碰                 | automatic property merge、tax/loan/legal authority、automatic contact、uncited buy/sell recommendation。                                                         |

## Stage 8 — Professional Workspace

| 項目                  | 規格                                                                                                                                                   |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Objective           | 將已驗證 modules組成 role/task-based Professional Mode，而非一次大爆炸重寫。                                                                                          |
| Scope               | purpose templates、persistent map、context header、evidence rail、task panel、module detail、Copilot、timeline、exports；Consumer shell保持簡潔。                  |
| Backend             | BFF/query composition、module permissions、workspace preferences、artifact/report orchestration、observability。                                          |
| Frontend            | `/workspace/{caseId}`；development/brokerage/due-diligence templates；responsive；deep link保留identity/context。                                          |
| Data                | 只展示每個 workspace可授權且coverage足夠的 modules；缺資料顯示not available。                                                                                           |
| New models          | workspace\_views, purpose\_templates, saved\_filters, dashboards, report\_templates。                                                                 |
| API                 | composed workspace summary、map feature query、task plan、module status、report/export jobs。                                                             |
| Tests               | end-to-end role journeys、large map dataset、keyboard/mobile/accessibility、cross-module identity consistency、consumer regression、permission snapshots。 |
| Acceptance criteria | 使用者從任何 module仍知道subject/purpose/next action；首頁仍只有主要任務；Consumer與Pro對同 evidence產生一致facts；無資料不出空白成功狀態。                                                  |
| Dependencies        | 每個啟用 module達production gate；Stage 7可選，不應阻擋無AI workspace。                                                                                             |
| Risk                | feature sprawl、map performance、permission composition、Consumer退化、release blast radius。                                                               |
| 不應碰                 | 同時啟用未驗證nationwide layers、工具清單首頁、AI-required core flow、big-bang removal of current journey。                                                           |

---

# 22. Risks / Licensing / Data Constraints

| Risk                             | Severity | 具體情境                                                   | Mitigation / Stop condition                                                  |
| -------------------------------- | :------: | ------------------------------------------------------ | ---------------------------------------------------------------------------- |
| Wrong identity                   | Critical | 地址 geocode掛錯 parcel/building，後續 title/valuation/CRM 全錯 | candidates + human confirm；no silent merge；conflict visible                  |
| Cadastral license                |   High   | 看得到地籍圖就誤以為可商業取 vector/WFS                              | service-by-service written approval；visual/query/vector權利分開                  |
| Listing ToS/copyright            | Critical | 自動抓15站、保存圖片文案、重新散布                                     | partner/user URL only；source terms registry；takedown/retention               |
| Electronic title automation      | Critical | 官方同意書禁止 automated extraction；個資處理不合目的                  | user upload/contracted partner；no scraping；privacy impact assessment         |
| Ownership/contact PII            | Critical | team member過度查看、匯出、外傳owner資料                           | tenant RLS、purpose/role, private storage, audit, redaction, retention        |
| Planning authority               |   High   | 過期／局部圖層被解讀為法定建築權利                                      | jurisdiction/effective version；official link；professional verification       |
| Hazard false safety              | Critical | provider unavailable/no-hit被總分當 low risk               | typed status contract；unknown blocks positive claim；production coverage gate |
| AI legal/valuation hallucination | Critical | 生成具體法律策略或無依據估價                                         | deterministic core、citations、claim validator、review/refusal                  |
| Cross-tenant leak                | Critical | title/contact/case經 Data API 或 Storage暴露               | grants + RLS tests、private schema/bucket、server-only service role            |
| Stale evidence                   |   High   | 舊title/listing/planning仍顯示current                      | effective/retrieved time、TTL/stale propagation、report version                |
| Provider dependency              |   High   | TGOS/NLSC/TDX quota、IP/domain、schema change            | adapter contract、health/status、cache under terms、fallback as unavailable     |
| Nationwide overclaim             |   High   | local open data pilot宣稱全臺                              | coverage registry；UI coverage boundary；jurisdiction rollout                  |
| Data maintenance cost            |   High   | 每個地方planning/building欄位各異                              | source registry、canonical mapping、quality dashboards、pilot sequencing        |
| Scope explosion                  |   High   | Consumer首頁塞滿16 modules                                 | two shells、task templates、feature gates、stage acceptance                     |
| Migration loss                   |  Medium  | local case import被誤當 verified property                 | `legacy_unverified` provenance；user confirm；no destructive local deletion    |

## Legal / product boundary

這份報告是產品與資料工程風險分析，不是法律意見。每個非開放資料來源在 production onboarding 前都需要 dataset/API-specific terms review；Government Open Data License 只適用明確採該授權發布的 dataset，不會自動涵蓋政府網站所有頁面、地籍向量、title或第三方 listing。

---

# 23. Final Recommended Product Positioning

## 23.1 建議定位

**PropTech AI Copilot 應定位成：臺灣不動產的 Property Decision Intelligence Platform——先確認標的身分，再把官方證據、現售市場、空間／法規／產權、風險與個人資金整合成可追溯的決策與專業行動。**
短版：

> **從「這是哪個標的」到「下一步該做什麼」的不動產證據與決策工作台。**

不要定位為：

- 另一個地籍圖台。
- iTaiwan clone。
- 泛用 CRM。
- 只會聊天的房地產 AI。
- 正式估價、法律、稅務、測量或銀行核貸替代品。

競爭護城河應是：`Property Identity Graph + Evidence Lineage + Deterministic Intelligence + Task-aware AI + Consumer/Professional dual shell`。

## 23.2 最後十問

### 1. 如果完全不考慮開發成本，iTaiwan 哪些功能值得我們拿？

值得吸收其完整工作鏈，而不是照抄畫面：地址／地號／建號 resolution、土地→地上建物、authorized parcel geometry、multi-parcel selection/color/measurement、building intelligence/XLSX、zoning/planning/old-house/urban-renewal、PLVR + active listing supply、title procurement/history/PDF、property-linked owner CRM、team permissions/history與map-linked export。再用 PropTech 的 valuation、risk、finance、tax與evidence AI重做 decision layer。

### 2. 如果只考慮未來 3 個月，最值得新增哪 5 個？

1. Property Identity Resolver + confirmation。
2. Durable Property/Case/Evidence persistence + workspace/RLS。
3. Multi-parcel GIS MVP（user geometry + legally usable layers；official status分開）。
4. Listing URL intake + sold-vs-asking observation，不做跨站 scraping。
5. Evidence-bound AI Brief，把 existing PLVR/valuation/location/terrain status/finance/tax串成引用式結論。

### 3. 哪些功能只是看起來很酷，但實際 User Value 不高？

沒有 task context 的大量 layer、任意土地上色、追求「15品牌」數字、疑似工廠等 niche layer、沒有 identity 的 cluster animation、為 AI 而 AI 的螢幕摘要。這些在特定專業情境可能有價值，但不應早於 identity、evidence與case continuity。

### 4. 哪些功能 iTaiwan 已經成熟到我們不應正面硬拼？

依官方更新呈現，iTaiwan 已把 address→land→building、parcel map/measurement、title procurement/team reuse、owner CRM、urban-renewal layers、15-brand listing map 做成連續專業 workflow。我們不應用三個月正面比資料廣度與每個 map tool；應以少量合法來源做深，主打 decision intelligence。

### 5. 哪些功能可以利用 AI 做得明顯比 iTaiwan 更好？

identity衝突偵測、source-cited evidence brief、PLVR comparable explanation、成交 vs 開價／降價／供給差異、title欄位引用與風險問題、planning/title/hazard矛盾、個人 affordability scenario、missing-evidence plan、CRM handoff與下一步。前提是 authoritative facts仍由 deterministic/provider layers供應。

### 6. 我們目前最大的架構缺口是什麼？

沒有 canonical-but-confirmable Property Identity 與 durable Case/Evidence backbone。現有 localStorage case只能保存分析摘要，無法保證不同 module談的是同一 parcel/building/listing，也不能支援title、CRM、team與跨裝置。

### 7. Property Case 是否應升級成更完整的 Property Entity / Case Graph？

**是，但不是把 Property Case 變成一張超大 JSON 表。** `PropertyEntity` 保存穩定且可版本化的身分；`Case` 保存某次購屋、開發、仲介或研究目的；Parcel/Building/Listing/Document/Contact/Evidence以typed temporal relations連接。現有 PropertyCase保留作 compatibility DTO。

### 8. Consumer Mode + Professional Mode 是否合理？

**合理，而且必要。** 兩者共用 resolution、graph、evidence、calculators、AI與artifact services；差別是 default case type、permissions、module visibility與資訊密度。禁止 fork兩套domain logic，也不讓Professional modules污染Consumer首頁。

### 9. 如果明天要 Demo，一條最強的完整使用流程應該是什麼？

若只用目前 repo：輸入條件找官方 PLVR 成交方向 → 鎖定地址／物件context → 看 Location 與明示 unknown 的 Terrain → 用 official comparables估值 → 代入開價算 loan/holding/tax → Viewing Decision → 保存兩件local cases比較 → 列印報告。Demo時必須誠實說 Property Finder不是在售案件、parcel/title/CRM不存在、terrain多數來源未ready。
若展示 VNext prototype：貼房仲網址／地址 → 看 identity candidates並確認 parcel+building → map選多筆土地／planning layers → 對照PLVR成交與asking price history → 上傳title並看page-cited摘要 → hazard/valuation/finance → AI Evidence Brief列「已知、衝突、未知、下一步」→ save case、compare、assign follow-up/export。這條流程最能同時展示 iTaiwan continuity 與 PropTech decision優勢。

### 10. 加入這些功能後，PropTech AI Copilot 最終到底應該定位成什麼？

它應該是 **Taiwan Property Decision Intelligence Workspace**：不是提供最多地圖按鈕，而是把一個真實土地／建物／listing的身分、來源證據、專業調查與個人／團隊決策連成一條可追溯 workflow；Consumer得到「是否值得進一步看」，Professional得到「這個案件下一步怎麼推進」。

---

## Final Go / No-Go Recommendation

- **GO**：Property Identity、durable Case/Evidence、user-safe GIS、task-based dual mode、evidence-bound AI 的 staged design。
- **CONDITIONAL GO**：building/planning/urban-renewal，先選 jurisdiction pilot並建立 coverage registry。
- **PARTNER GATE**：direct title procurement、cross-brand listing aggregation、nationwide cadastral vector。
- **NO-GO**：scraping title/listing sites、reverse engineering iTaiwan、把 mock/provider unknown當 production、首頁工具化、在 evidence layer完成前上線自由型 decision AI。

本報告完成後應停止於 architecture decision。下一個 Kiro 階段只應從 Stage 0 開始，不應直接跳到「仿 iTaiwan 功能開發」。