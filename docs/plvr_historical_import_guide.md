# PLVR 歷史資料匯入指南

本流程用於維護者受控匯入雙北近一年官方 PLVR 資料。它不會下載全台資料，也不應在 Render runtime 執行。

## 首次準備

1. 在 Supabase SQL Editor 依序執行：
   - `database/migrations/001_add_dedupe_key_to_real_price_transactions.sql`
   - `database/migrations/002_expand_valuation_import_runs.sql`
2. 僅在本機或受控 CI 設定 `VALUATION_DATABASE_URL`。
3. 將多期 ZIP 放在 `data/raw/plvr/history/`。此路徑已被 `.gitignore` 排除，不可 commit。

## 先做 Dry-run

```powershell
python scripts/import_plvr_to_postgres.py --input data/raw/plvr/history --cities 台北市,新北市 --districts 大安區,信義區,板橋區 --since 2025-01 --until 2026-12 --limit 5000 --dry-run
```

先檢查 `accepted_rows`、排除原因、來源期間、城市／行政區統計與 `estimated_growth`。資料夾批次匯入未指定城市時會停止；超過 10,000 筆且未加入 `--confirm-large-import` 時也會停止。

## 匯入雙北近一年

確認 dry-run 後，在受控環境執行：

```powershell
python scripts/import_plvr_to_postgres.py --input data/raw/plvr/history --cities 台北市,新北市 --districts 大安區,信義區,板橋區 --since 2025-01 --until 2026-12 --limit 5000
```

匯入器優先使用官方編號／移轉編號；沒有識別欄位時，以來源、城市、行政區、地址、交易期間、建物型態、坪數、總價與單價建立 `dedupe_key`。相同 `source + dedupe_key` 會跳過，不會再次插入。

正式寫入採 temporary staging table 分批寫入，預設每批 200 筆、每 100 筆顯示進度、單一 statement timeout 30 秒：

```powershell
python scripts/import_plvr_to_postgres.py --input data/raw/plvr/history --cities 台北市,新北市 --districts 大安區 --since 2025-01 --until 2026-12 --limit 100 --max-write-rows 100 --chunk-size 200 --progress-every 100 --statement-timeout 30
```

若單一 chunk timeout，該 chunk 會回滾並顯示失敗筆數範圍。可先用 `--max-write-rows 100` 做小範圍正式寫入測試。

## Report 與安全界線

Report 包含讀取、接受、插入、更新、重複跳過、排除、檔案數、範圍、資料庫匯入前後筆數與估計成長。`valuation_import_runs` 保存最近匯入範圍與結果。

目前逐步擴充六都近三年資料。不要一次灌入全台多年逐筆資料，避免 Supabase 容量、索引與查詢效能失控。三年以前若需要長期觀察，未來應建立統計摘要表。

## 六都近三年匯入準備

`data/raw/plvr/pending_liudu/` 僅作為本機或受控 CI 的 pending folder，不可 commit。本階段只準備指令，不直接執行匯入。

先做整體 dry-run：

```powershell
python scripts/import_plvr_to_postgres.py --input data/raw/plvr/pending_liudu --cities "桃園市,台中市,台南市,高雄市" --since 2024-01 --until 2026-12 --limit 250000 --dry-run
```

確認報告後，建議分城市正式執行：

```powershell
python scripts/import_plvr_to_postgres.py --input data/raw/plvr/pending_liudu --cities "桃園市" --since 2024-01 --until 2026-12 --limit 80000 --chunk-size 300 --progress-every 300 --statement-timeout 30 --confirm-large-import
python scripts/import_plvr_to_postgres.py --input data/raw/plvr/pending_liudu --cities "台中市" --since 2024-01 --until 2026-12 --limit 100000 --chunk-size 300 --progress-every 300 --statement-timeout 30 --confirm-large-import
python scripts/import_plvr_to_postgres.py --input data/raw/plvr/pending_liudu --cities "台南市" --since 2024-01 --until 2026-12 --limit 80000 --chunk-size 300 --progress-every 300 --statement-timeout 30 --confirm-large-import
python scripts/import_plvr_to_postgres.py --input data/raw/plvr/pending_liudu --cities "高雄市" --since 2024-01 --until 2026-12 --limit 100000 --chunk-size 300 --progress-every 300 --statement-timeout 30 --confirm-large-import
```

城市比較會正規化 `臺北市／台北市`、`臺中市／台中市`、`臺南市／台南市`。每次正式匯入後，先檢查 data-status，再依 [PLVR Rolling 3 年資料保留策略](plvr_retention_policy.md) 執行 prune dry-run。
