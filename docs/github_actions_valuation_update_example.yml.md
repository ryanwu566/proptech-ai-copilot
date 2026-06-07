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
        run: python scripts/update_valuation_data.py --local-zip /tmp/official-data.zip --database-url "$VALUATION_DATABASE_URL"
```

原始 ZIP 應存放在 runner 暫存空間，不可 commit 到 GitHub。資料庫憑證只能由 GitHub Secrets 提供。
