# PLVR Rolling 5 年資料保留策略

## 政策目標

估價資料庫採 **rolling 5 年官方 PLVR** 保留策略。資料庫可保留少量展示樣本，但清理工具只處理 `source = official_plvr_opendata`，不會刪除展示樣本、社區索引或匯入紀錄。

採 rolling 5 年的理由：

- 估價與趨勢分析更重視近期市場條件，長期永久累積未必提升當期判讀品質。
- 控制 Supabase/Postgres 儲存、索引與查詢成本。
- 降低維護者誤匯全台多年資料後造成容量與效能風險。
- 保留可稽核的季度更新與清理流程，而不是讓使用者手動刪資料。

## 每季更新流程

1. 維護者取得新的官方季度 ZIP。
2. 將 ZIP 放入本機或受控 CI 的 pending folder；raw ZIP 不可 commit。
3. 執行 importer dry-run，確認城市、期間、筆數與排除原因。
4. 分城市正式匯入，依 `source + dedupe_key` 跳過重複資料。
5. 檢查 `/valuation/data-status` 的官方筆數、有效期間與最近匯入範圍。
6. 執行 prune dry-run，盤點 rolling 5 年外資料。
7. 經維護者確認後，才使用 `--confirm-delete` 清理舊官方資料。

ETL 與 prune 不在 Render runtime 執行。`VALUATION_DATABASE_URL` 只能放在本機安全環境、Supabase 設定或受控 CI secret，不可寫入 repo。

## 安全清理

預設 dry-run：

```powershell
python scripts/prune_valuation_data.py --keep-years 5 --dry-run
```

盤點指定城市與期間：

```powershell
python scripts/prune_valuation_data.py --before 2021-01 --cities "台北市,新北市" --dry-run
```

確認報告後才允許刪除：

```powershell
python scripts/prune_valuation_data.py --before 2021-01 --cities "台北市,新北市" --confirm-delete
```

Report 包含 `cutoff_period`、`matched_rows`、`rows_by_city`、`rows_by_period`、`will_delete`、`status` 與安全警告。

## 安全界線

- 只處理 `official_plvr_opendata`。
- 不刪 `real_price_sample`、`mock_fallback`。
- 不刪 `valuation_import_runs`、`community_buildings`。
- 沒有 `--confirm-delete` 不會刪除。
- 同時傳入 `--dry-run --confirm-delete` 時仍不會刪除。
- 不下載資料、不匯入資料、不在 Render runtime 執行。
