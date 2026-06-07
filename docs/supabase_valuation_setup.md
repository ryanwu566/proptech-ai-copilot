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
