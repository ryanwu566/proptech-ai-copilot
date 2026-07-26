# PLVR Data Freshness & Import Operations v1

本文件描述官方 PLVR 匯入完成後的資料新鮮度與匯入品質判讀。它是維運提示，不是估價準確度、交易保證或購買建議。

## Freshness 狀態

- `fresh`：最近完成匯入不超過 120 天，且最新有效期別落後不超過 4 個日曆月。
- `aging`：尚未達 stale，但匯入超過 120 天或有效期別落後超過 4 個日曆月。
- `stale`：匯入超過 210 天，或有效期別落後超過 7 個日曆月。
- `unknown`：匯入狀態、匯入時間或有效期別缺漏／格式無法確認。
- `no_official_data`：目前沒有可確認的官方 PLVR 交易資料。
- `unavailable`：資料庫或 provider 暫時無法讀取。

新鮮度計算使用 UTC 與日曆月份，不以固定天數近似月份。`unknown`、`no_official_data`、`unavailable` 都需要維運人員確認，不會被解讀為零交易或低風險。

## Dry-run 與報告

1. 先以 `--dry-run` 檢查本機提供的官方檔案、範圍、期間與排除原因。
2. 需要保存安全報告時使用 `--report-output <path>`；報告以暫存檔寫入後原子替換，且不包含原始列、地址、資料庫設定或錯誤細節。
3. 需要阻擋品質不足的自動化流程時加上 `--quality-gate`。
4. `python scripts/audit_plvr_import_report.py --input <report-json>` 可唯讀檢查報告。

Quality reason codes：`no_rows_read`、`no_rows_accepted`、`no_valid_source_period`、`large_import_confirmation_required`、`high_exclusion_ratio`、`high_duplicate_ratio`、`scope_missing`、`report_input_invalid`。

`pass` 與 `warning` 的 quality gate exit code 為 0；`blocked` 為 2；技術或格式錯誤為 1。高排除比例（超過 25%）或高重複比例（超過 50%）是 warning；沒有讀到資料、沒有可接受資料、沒有合法期間、缺必要範圍或需要大批次確認是 blocked。

## Supabase／Postgres 維運

若估價資料庫暫停或連線失敗，應從 `/valuation/data-status` 的 `unavailable` 與 attention 狀態辨識，不在 Render runtime 執行 PLVR 下載或 ETL。Render 只提供既有查詢能力；匯入應由受控的離線操作環境完成。

匯入前確認：來源是官方 PLVR 買賣資料、行政區範圍明確、期間可辨識、dry-run 通過、排除與重複比例已檢視，並確認大批次操作需要明確旗標。

匯入後依序檢查：`/valuation/data-status` → Market Coverage reconcile → Market Insight。沒有資料、資料不足或 `unknown`／`unavailable` 不得描述成 0 筆、沒有交易或低風險。

資料新鮮度只描述資料維運狀態，不代表個別估價準確度，也不會自動修改估價、貸款、稅務或看房決策。
