# Supabase / Postgres 估價資料庫設定

本文件建立可用的估價資料庫骨架。現階段只匯入展示樣本，不下載全台資料，也不在 Render runtime 執行 ETL。

## 1. 建立 Supabase Project

在 Supabase 建立新 project，妥善保存 database password。不要將密碼、connection string 或 `.env` commit 到 repo。

## 2. 建立資料表

開啟 Supabase SQL Editor，執行：

```text
database/valuation_schema.sql
```

Schema 包含：

- `real_price_transactions`
- `community_buildings`
- `valuation_import_runs`
- 地區、路段、建物類型、交易期間與經緯度索引

## 3. 取得連線字串

至 Project Settings 的 Database／Connection string 取得 Postgres 連線字串。建議使用 Supabase 提供、適合部署環境的連線方式。

## 4. 設定 Render Backend

在 Render backend 設定：

```text
VALUATION_DATABASE_URL=postgresql://...
```

FastAPI 只在第一次使用估價 provider 時連線。若連線失敗，系統會安全回退至 SQLite、sample 或展示資料；`/health` 不依賴估價資料庫。

Vercel 不需要且不應設定 `VALUATION_DATABASE_URL`。

## 5. 匯入展示樣本

在本機或 GitHub Actions 設定 `VALUATION_DATABASE_URL` 後執行：

```powershell
python scripts/seed_valuation_sample_to_postgres.py
```

此命令只匯入：

- `data/real_price_sample.csv`
- `data/community_building_sample.csv`

匯入後 `/valuation/data-status` 會顯示 `active_source=postgres`，並明確標示資料仍為展示樣本、尚非全台完整資料。

## 6. 未來正式更新

正式資料應由 GitHub Actions 或獨立後台排程下載官方實價登錄 OpenData、清洗成標準欄位並 upsert 至 Supabase/Postgres。不可在 Render runtime 執行下載或 ETL，也不可 commit raw ZIP。

## 7. 手動匯入官方 PLVR OpenData

目前提供受控的手動匯入工具，不會自動下載資料：

先在 SQL Editor 依序套用：

```text
database/migrations/001_add_dedupe_key_to_real_price_transactions.sql
database/migrations/002_expand_valuation_import_runs.sql
```

```powershell
python scripts/import_plvr_to_postgres.py --input C:\temp\plvr.zip --city 台北市 --dry-run
python scripts/import_plvr_to_postgres.py --input C:\temp\plvr.zip --city 台北市
```

工具會：

- 從 ZIP 或 CSV 辨識買賣實價登錄主檔，排除 schema、manifest、預售與租賃資料。
- 依序嘗試 `utf-8-sig`、`utf-8`、`cp950`、`big5`。
- 將民國交易年月轉為 `YYYY-MM`，平方公尺轉為坪，元轉為萬元。
- 缺少每平方公尺單價時，使用總價與面積計算每坪單價。
- 排除缺少地點、日期、面積、總價或異常單價的資料，並輸出品質檢查統計。
- 正式匯入時寫入 `real_price_transactions` 與 `valuation_import_runs`。
- 以 `source + dedupe_key` 避免相同官方交易重複插入，並安全回填既有官方資料的 dedupe key。
- 支援資料夾、多城市／行政區、`--since`、`--until` 與大型匯入防呆。

可使用 `--district`、`--road`、`--limit` 縮小範圍。`--replace-scope` 只允許搭配明確城市、行政區或路段使用。

正式匯入必須在本機或受控 CI 設定 `VALUATION_DATABASE_URL`。Vercel 不需要此變數，Render runtime 也不會自動執行匯入。

目前官方資料僅涵蓋台北市大安區與新北市板橋區部分期間，尚非完整雙北一年、雙北五年或全台資料。
