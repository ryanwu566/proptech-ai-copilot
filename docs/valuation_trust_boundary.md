# Valuation Trust Boundary v1

估價、趨勢與物件搜尋只會把可驗證的官方 PLVR 結果標記為可操作結果。

## Provider boundary

- 正式模式必須有可用的 PostgreSQL valuation provider。
- PostgreSQL 未設定、連線失敗或查詢失敗時，回傳 `unavailable`，不會自動改用 SQLite、sample 或 mock 資料。
- 展示資料只有在明確設定 `VALUATION_DEMO_MODE` 後才可使用，且結果標記為 `demo`、不可操作。

## Result states

`available` 需要至少三筆有效、正數且來源為官方 PLVR 的可比成交；`no_data` 表示 provider 正常但資料不足；`unavailable` 表示 provider 或結果無法安全確認；`demo` 僅供展示。

非 `available` 狀態的估價數字、價格區間、趨勢數字與預測均為 `null` 或空集合，不會以 0 代表缺資料，也不會進入正式案件、分享或貸款帶入流程。

## Public contract

公開 response 只保留 allowlist 的來源摘要與安全 reason code，不回傳 raw provider payload、錯誤細節、SQL、連線資訊或 credential。趨勢與物件搜尋同樣使用 `available`、`no_data`、`unavailable` 與 `is_actionable` 狀態欄位。

資料不足不是低價、低風險或零成交結論；使用者仍應依既有免責說明進行人工查核。
