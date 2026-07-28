# Terrain & Disaster Risk Audit v1

## 1. Executive Summary

目前 repository 有一條可呼叫的 Terrain Risk API、地址定位流程、四個 provider adapter，以及前端的地勢與災害狀態呈現。但這些程式碼不足以證明正式災害資料已完整納編、全臺覆蓋或正式站結果正確。

- ARDSWC MVT provider 對山崩／地滑與土石流有可執行的外部圖磚查詢實作，分類為 `partial`。它有官方來源名稱、MVT 資料年度與 fake/fixture 測試，但沒有 repository 內快照或全臺 coverage proof。
- NLSC 地形／坡度／高程、WRA 淹水、GeologyCloud 地質敏感／液化／活動斷層 provider 都明確回傳 `unavailable`，不能視為沒有風險。
- 前端能顯示圖層狀態、來源名稱、來源機關、資料日期或 `unknown`，並有保守提醒；但現有流程也保存 terrain result，且 `risk-summary` 會讀取 terrain level，這是後續 trust-boundary review 的已確認缺口。
- repository 沒有災害資料快照、資料庫圖資或可驗證的全臺覆蓋清單。地址可透過既有位置搜尋取得座標，或由使用者直接提供座標；本 audit 未呼叫任何 provider。
- 所有資料不足、未評估或暫時不可用的狀態都必須維持保守語意：資料不足不代表沒有風險。

本階段不能進正式站驗收，`RELEASE_DECISION=NO_GO`。

## 2. Current Architecture Map

```text
address/city/district/road or explicit coordinates
  -> backend/api/routes_terrain_risk.py
  -> services/terrain_risk_service.py
  -> existing map_service.search_location when coordinates are absent
  -> NLSC / ARDSWC / WRA / GeologyCloud provider adapters
  -> per-layer status, overall reference result, source_transparency
  -> frontend_next/components/terrain-risk-analysis.tsx
  -> TerrainStatusMatrix and LocationMarketStage
  -> existing runtime/session and Property Case data flows
```

主要程式位置：

- Frontend: `frontend_next/components/terrain-risk-analysis.tsx`, `frontend_next/components/data-visualization/terrain-status-matrix.tsx`, `frontend_next/components/guided-journey/location-market-stage.tsx`。
- API route: `backend/api/routes_terrain_risk.py`, 端點為 `POST /terrain-risk/analyze`。
- Service: `services/terrain_risk_service.py`。
- Providers: `services/terrain_risk_providers/` 下的 NLSC、ARDSWC、WRA 與 GeologyCloud adapters。
- Property Case: `frontend_next/lib/property-case.ts`, `frontend_next/lib/property-case-evidence.ts`, `frontend_next/lib/case-storage.ts`。
- Tests: terrain API、service、provider、transparency 與 frontend static contract tests。

## 3. Hazard Capability Matrix

詳細 machine-readable matrix 位於 `docs/terrain-disaster-risk-capability-matrix-v1.json`。

| 項目 | capability state | provider kind | 來源證據 | coverage | 目前限制 |
| --- | --- | --- | --- | --- | --- |
| 地形／坡度 | unavailable | placeholder | NLSC adapter 與機關名稱 | unknown | 沒有直接點位查詢或資料 asset |
| 高程／地形 | unavailable | placeholder | NLSC adapter 與機關名稱 | unknown | 沒有高程結果、版本或日期 |
| 淹水潛勢 | unavailable | placeholder | WRA adapter 與機關名稱 | unknown | 未設定座標查詢 API |
| 土壤液化 | unavailable | placeholder | GeologyCloud adapter 與機關名稱 | unknown | 未設定直接比對 API |
| 山崩與地滑 | partial | live_external | ARDSWC MVT adapter、官方 agency 與年度字串 | 未證明 | 沒有全臺 coverage proof，依賴外部 MVT 與 decoder |
| 土石流潛勢溪流 | partial | live_external | ARDSWC MVT adapter、官方 agency 與年度字串 | 未證明 | 沒有 repository snapshot 或完整 freshness |
| 活動斷層 | unavailable | placeholder | GeologyCloud adapter 與機關名稱 | unknown | 目前沒有座標比對結果 |
| 地質敏感區 | unavailable | placeholder | GeologyCloud adapter 與機關名稱 | unknown | 沒有資料 asset、版本與 coverage |

## 4. Provider Inventory

### NLSC

`services/terrain_risk_providers/nlsc_terrain_provider.py` 建立 `NlscTerrainProvider`，來源文字指向內政部國土測繪中心。`analyze` 不查詢網路或資料檔，固定產生 slope/elevation 缺值與 `unavailable`。因此是官方來源 metadata 的 placeholder，不是 official live 或 snapshot。

### ARDSWC

`services/terrain_risk_providers/ardswc_slope_hazard_provider.py` 建立 `ArdswcSlopeHazardProvider`，使用公開 MVT tile adapter，處理 tile、decoder、線／多邊形與半徑匹配。程式保留 tile error、`limited`、`error`、`matched=false` 與 `level=unknown`。測試以 fake HTTP 與 decoder 驗證，不代表 production external call 已完成，因此分類為 partial。

### WRA

`services/terrain_risk_providers/wra_flood_provider.py` 建立 `WraFloodProvider`，來源文字指向經濟部水利署，但目前沒有合法直接查詢座標淹水級距的設定，固定回傳 `unavailable`。沒有資料 asset、版本、日期或 coverage proof。

### GeologyCloud

`services/terrain_risk_providers/geologycloud_provider.py` 將地質敏感區、土壤液化與活動斷層分成三個 layer，來源文字指向地質雲與主管機關，但目前固定回傳 `unavailable`。它是 provider-shaped placeholder，不是已整合的正式資料源。

## 5. Data Source Evidence

來源名稱與機關名稱只來自 provider adapter 的 source metadata。ARDSWC 額外有 `113年度（官方公開 MVT）` 的資料年度與 `limited` quality；其他 provider 沒有 data version 或 freshness。repository 沒有下載的災害圖資、快照、seed、CSV、JSON 或資料庫 table 可供查核。

因此：

- 官方來源名稱：有 repository 字串證據。
- 官方資料實際可用：只有 ARDSWC adapter 有部分可執行路徑；其餘明確 unavailable。
- 即時性：無法證明。ARDSWC 年度字串不是完整更新時間，也不是正式站 freshness proof。
- 覆蓋：無法證明全臺。行政區或地址輸入存在，不等於圖資 coverage 存在。

## 6. Geographic Coverage Evidence

目前只能確認 ARDSWC 會依座標與半徑計算 MVT tile；不能從 repository 證明全臺、縣市或行政區完整覆蓋。NLSC、WRA、GeologyCloud 沒有可執行的資料查詢，因此 coverage 是 `unknown`。沒有任何資料 asset 或 coverage registry 支持 `nationwide` 宣稱。

## 7. Address and Spatial Matching Flow

後端接受地址、縣市、行政區、路段或成對座標。若沒有成對座標，service 以既有 `map_service.search_location` 對組合查詢定位；找不到 center 時拋出定位錯誤並由 route 回 422。若有座標，直接建立 resolved location。

ARDSWC 以 WGS84 形式的 latitude/longitude 計算 tile，解析 MVT geometry，再做點、線或多邊形與 radius 的距離／相交判定。repository 有 tile-to-coordinate 與 geometry matching 程式，但沒有可供本 audit 證明的 CRS registry 或全臺圖資驗證。其他 provider 沒有實際 spatial matching。

找不到地址與 provider failure 有區分：地址定位失敗是 422；ARDSWC tile failure 是 `error` 或 `limited`；未命中是 `available` + `matched=false` + `unknown` level；明確 unavailable 是 `unavailable`。這些狀態仍需下一階段確認是否在所有下游保持一致。

## 8. State Contract Audit

已從 service 與 tests 證實：

- `unavailable` 不會直接產生 low risk，overall 會偏向 `unknown`。
- ARDSWC 部分 tile 失敗不會偽裝成 no-hit；`limited` 會保留。
- ARDSWC 成功但沒有命中時使用 `matched=false` 與 `level=unknown`。
- 未選取的 layer 使用 `skipped`，source transparency 映射為 `not_assessed`。
- source transparency 的 coverage 在 unavailable／not_assessed 時為 `unknown`；缺日期時顯示 `unknown`。

已確認的風險：

- `services/terrain_risk_service.py` 仍會產生一個 overall level；需要後續確認它不被產品解讀為綜合安全分數。
- `frontend_next/lib/risk-summary.ts` 會讀取 terrain overall level 並加入 risk/positive factors；這表示目前不能只憑 UI 文案宣稱 terrain 完全不影響 decision summary。
- `frontend_next/lib/case-storage.ts` 與相關頁面保存 terrain 結果切片；需要後續建立 explicit evidence 與 privacy boundary。

## 9. Frontend Presentation Audit

`TerrainRiskAnalysis` 與 `TerrainStatusMatrix` 顯示地形／坡度、淹水、坡地災害、地質敏感、土壤液化、活動斷層等項目。前端有 source metadata、狀態、資料年度／日期 fallback、官方圖台入口與「資料不足不代表低風險」文案。source transparency 使用 allowlisted fields，不直接渲染 raw provider payload、座標或 token。

限制：沒有完整 source version、freshness 或 coverage registry；主要 overall 卡仍可能讓使用者把 level 當成綜合結果。後續必須讓不可用、未評估、未命中與有限覆蓋在視覺上保持保守，不增加安全分數或推薦。

## 10. Property Case Transfer Audit

terrain result 有 runtime/session event，並被既有 case storage 與 comparison/readiness 相關資料流讀取。既有 tests 證明資料切片與風險因素會流動，但不能證明這符合「reference evidence only」的產品界線。未發現本 audit 期間新增自動保存或 transfer；目前既有路徑需在後續 Phase 2／5 明確限制：不可自動寫案件、不可影響 valuation／loan／tax、不可影響 ranking／winner／購買建議。

## 11. Privacy and Error Boundary Audit

目前 transparency UI 的 tests 會禁止 source URL、座標、raw、token、secret 等敏感欄位直接出現在來源卡。service 與 route 的輸出仍包含 input/resolved location 供既有分析流程使用，因此後續應繼續確認 API log、case storage 與 report export 不會擴散 raw coordinates、provider payload、SQL、stack trace、internal headers 或 credential。

## 12. Existing Test Coverage

- `tests/test_terrain_risk_api.py`: route 存在、request validation、穩定輸出欄位、定位失敗 422。
- `tests/test_terrain_risk_service.py`: 座標優先、地址定位 fallback、provider failure、不使用 unavailable 當 low risk、layer filter 與 risk factor 行為。
- `tests/test_terrain_risk_providers.py`: fake provider、MVT tile range、線／多邊形匹配、dedupe、partial tile failure、全失敗、invalid decoder 與 no-hit unknown。
- `tests/test_terrain_risk_transparency.py`: source transparency allowlist、來源日期 fallback、unavailable caveat、風險結果不變與敏感欄位排除。
- `tests/test_frontend_terrain_risk.py`: frontend API flow、圖層、官方來源入口、session/event 與既有 case/report data flow。
- `tests/test_frontend_terrain_risk_transparency.py`: source fields、保守提醒、UI 不顯示 raw provider fields、無新增 API/storage，以及 viewing-decision 檔案未接 transparency。

這些 tests 都使用 fake、fixture、monkeypatch 或 static source checks；沒有在本 audit 執行真實 provider。

## 13. Confirmed Gaps

### P0

- 目前無證據顯示假安全已被所有下游邊界阻斷；terrain overall level 仍進入 `risk-summary`，應先完成 false-safety review。
- 若使用者把 overall level 當成綜合安全判定，會超出 reference evidence 邊界。

### P1

- ARDSWC 的全臺 coverage、資料 freshness、production execution 與外部依賴尚未驗證。
- NLSC、WRA、GeologyCloud 沒有直接資料查詢或 snapshot，無法支援正式多災害比對。
- Property Case 已有 terrain result 保存／呈現路徑，尚缺明確 trusted evidence transfer contract。

### P2

- 缺少統一的 source version、freshness、coverage metadata registry。
- 缺少 no-match、provider error、not_assessed 在所有 frontend/report/export 路徑的端到端 contract tests。
- CRS 與資料圖層版本的可追溯性不足。

### P3

- 需要更清楚的官方圖台補查操作指引與多地貌人工案例清單。

## 14. Risk-ranked Remediation Plan

1. Phase 2：State Contract and False-Safety Repair。固定 unknown、not_assessed、unavailable、no-match 與 provider error 的下游語意，移除任何假安全解讀。
2. Phase 3：Official Data Source Integration。逐項決定正式來源、資料授權、版本、更新與可執行查詢或 snapshot，不把 placeholder 當資料。
3. Phase 4：Spatial Matching and Coverage Validation。建立 CRS、geometry、buffer、coverage registry 與跨縣市驗證案例。
4. Phase 5：Frontend Evidence and Property Case Integration。只顯示最小 evidence metadata，並以 explicit reference-only guard 控制案件傳遞。
5. Phase 6：Production Acceptance。完成多地貌、多狀態、手機／桌機與人工官方圖台比對後，才重新評估 release。

## 15. Definition of Done

正式完成至少必須有：每項災害明確 capability state、官方來源證據、可證明 coverage、可解釋 spatial matching、no-match 與 no-risk 分離、provider failure fail closed、unknown 保留、source/version/freshness 可見、沒有總分／排名／購買建議、完整 contract tests，以及正式站多地貌案例驗收。

## 16. Release Decision

本階段只完成 repository audit、矩陣與契約測試，沒有真實 provider、資料庫或正式站呼叫。`RELEASE_DECISION=NO_GO`，不得宣稱 terrain production accepted、production ready 或正式站通過。
