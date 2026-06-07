# GitHub Actions 估價資料更新範例

以下內容僅供未來啟用參考，不應直接放入 `.github/workflows`，也不會在目前專案自動執行。

```yaml
name: Update valuation database

on:
  schedule:
    # 每月 2、12、22 日台灣時間清晨執行
    - cron: "0 20 1,11,21 * *"
  workflow_dispatch:

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install updater dependencies
        run: pip install -r requirements.txt
      - name: Download official batch data to temporary storage
        run: echo "Replace with reviewed official OpenData download command"
      - name: Normalize and upsert external database
        env:
          VALUATION_DATABASE_URL: ${{ secrets.VALUATION_DATABASE_URL }}
        run: python scripts/import_plvr_to_postgres.py --input /tmp/official-data.zip --cities 台北市,新北市 --since 2025-01 --dry-run
      - name: Import reviewed official PLVR data
        env:
          VALUATION_DATABASE_URL: ${{ secrets.VALUATION_DATABASE_URL }}
        run: python scripts/import_plvr_to_postgres.py --input /tmp/official-data.zip --cities 台北市,新北市 --since 2025-01
```

原始 ZIP 應存放在 runner 暫存空間，不可 commit 到 GitHub。資料庫憑證只能由 GitHub Secrets 提供。

正式流程應在每月 2、12、22 日後執行：下載官方實價登錄 OpenData、清洗為 `database/valuation_schema.sql` 的標準欄位，再以 `source + dedupe_key` 去重寫入 Supabase/Postgres。不可 commit raw ZIP，也不可在 Render runtime 執行 ETL。

下載步驟必須由團隊審查並鎖定官方來源；目前 repo 不提供自動下載命令，也不會建立可自動執行的 workflow。建議先跑 `--dry-run`，審查接受筆數與排除原因後才執行正式匯入。

首次驗證資料庫 schema 時，可改用展示樣本 seed：

```yaml
- name: Seed bundled valuation sample
  env:
    VALUATION_DATABASE_URL: ${{ secrets.VALUATION_DATABASE_URL }}
  run: python scripts/seed_valuation_sample_to_postgres.py
```
