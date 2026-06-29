# Product Capability Surface v1

本文件盤點正式專案目前已具備的使用者可見能力，目的在於讓首頁「物件決策工作台」只呈現真正可操作的入口。狀態分類固定為 `ready_and_connected`、`ready_but_not_exposed`、`needs_user_input`、`backend_only`、`unavailable`。

| 能力名稱 | 現有前端入口 | 後端／服務依賴 | 盤點狀態 | 本次工作台入口 | 是否可在正式環境操作 | 阻塞原因（若有） |
| --- | --- | --- | --- | --- | --- | --- |
| 找物件 | `frontend_next/components/property-finder.tsx` | `POST /valuation/property-search`, `services/property_search_service.py` | ready_and_connected | Step 1 找物件 | 是 | 無 |
| 位置洞察 | `frontend_next/components/location-insight.tsx` | `POST /location/insight`, `services/location_insight_service.py` | needs_user_input | Step 2 看位置 | 是 | 需要地址或路段輸入 |
| 地勢／災害風險 | `frontend_next/components/terrain-risk-analysis.tsx` | `POST /terrain-risk/analyze`, `services/terrain_risk_service.py`, `services/terrain_risk_providers/` | needs_user_input | Step 2 看位置 | 是 | 需要可解析位置；資料 unavailable 不代表低風險 |
| 通勤與生活機能 | `frontend_next/components/commute-livability-card.tsx` | `POST /commute/address-lookup`, in-memory TDX snapshot | needs_user_input | Step 2 看位置 | 是 | 需要使用者手動查詢，且正式後端需先完成快照刷新 |
| 地圖洞察 | `Map Insight Lite` page in `frontend_next/app/page.tsx` | `/map/search`, `/map/nearby`, `/map/insight`, `services/map_service.py` | ready_and_connected | 側欄「地圖」與 Step 2「在地圖查看」 | 是 | 無 |
| 市場資訊 | `Market Insight Lite` page in `frontend_next/app/page.tsx` | `/market-insights`, `services/market_insight_service.py` | ready_and_connected | Step 3 算價格與資金、更多工具 | 是 | 無 |
| 估價 | `frontend_next/app/page.tsx` Valuation page | `/valuation/estimate`, `/valuation/trend`, valuation services | ready_and_connected | Step 3 算價格與資金 | 是 | 無 |
| 貸款／資金能力 | `frontend_next/components/loan-calculator.tsx`, `Aegis-Credit Lite` | `/loan/calculate`, `/aegis-credit/analyze`, bank and mortgage rate routes | ready_and_connected | Step 3 算價格與資金 | 是 | 無 |
| 稅費 | `TaxOracle` page in `frontend_next/app/page.tsx` | `/taxoracle/analyze`, `/taxoracle/report`, `services/tax_service.py` | ready_and_connected | Step 3 稅務快篩與更多工具 | 是 | 無 |
| 法律風險 | TaxOracle rule trace and document reminder surfaces | `/taxoracle/analyze` deterministic rules | needs_user_input | Step 3 稅務快篩 | 是 | 目前只提供稅務與文件風險快篩，非正式法律意見 |
| 案件儲存 | `frontend_next/components/case-manager.tsx` | browser local storage only | ready_and_connected | Step 4 比較與做決策 | 是 | 只保存在使用者瀏覽器 |
| 案件比較 | `frontend_next/components/case-comparison-panel.tsx` | `frontend_next/lib/case-comparison.ts` | needs_user_input | Step 4 比較與做決策 | 是 | 需先選擇 2 至 3 個已儲存案件 |
| 列印／儲存 PDF | `frontend_next/components/print-comparison-report.tsx`, browser print | browser print | ready_and_connected | Step 4 比較與做決策 | 是 | 使用瀏覽器列印或另存 PDF，不使用伺服器端 PDF |
| 後端通勤快照刷新 | 無前端入口；GitHub Actions 手動 workflow | `POST /commute/refresh`, Render runtime secrets | backend_only | 不放入工作台可點擊功能 | 否 | 管理者營運工具，前端不得呼叫 |

## 工作台呈現原則

- `ready_and_connected` 能力可以提供清楚入口。
- `needs_user_input` 能力可以提供入口，但必須說明需要地址、物件條件或已儲存案件。
- `backend_only` 能力不得做成一般使用者可點擊功能。
- `unavailable` 能力不得宣稱可用，也不得以假資料偽裝完成。
- 通勤資訊只作通勤與生活機能參考，不影響地勢災害、貸款、法律、稅務、估價或看房決策。
- 資料不足、provider unavailable、not assessed 或 unknown 不得呈現為低風險或安全。
