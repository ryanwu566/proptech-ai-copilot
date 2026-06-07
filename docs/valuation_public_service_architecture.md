# 房價估算普及化架構

## 使用者流程

使用者只需要在網站選擇縣市、行政區、路段、建物條件，並可選填社區或建案名稱。系統回傳可比成交估算、估值區間、信心分數、估價層級與資料更新時間。

使用者不需要下載 CSV、處理 ZIP，也不需要執行資料更新 script。

## 系統維護流程

正式版本可由排程取得官方實價登錄 OpenData 批次資料，完成清洗、欄位標準化、社區與路段索引後，寫入 Supabase/Postgres。FastAPI 僅查詢已整理完成的資料庫。

```text
官方實價登錄 OpenData
→ GitHub Actions / Scheduler
→ 下載、清洗、標準化與索引
→ Supabase / Postgres
→ FastAPI 查詢
→ Next.js 顯示
```

目前版本依序嘗試：

1. `VALUATION_DATABASE_URL` 對應的 Supabase/Postgres provider
2. `data/processed/valuation_index.sqlite`
3. `data/real_price_sample.csv`
4. 記憶體展示資料 fallback

Provider 在第一次呼叫估價或資料狀態 API 時才初始化。`/health` 不讀取估價資料。

Postgres provider 先以地區條件縮小查詢，再依路段、建物類型、面積、屋齡、交易期間與經緯度排序，最多取 50 筆候選交由共用 Python 估價邏輯處理。連線失敗時會安全回退至下一個 provider。

## 官方 PLVR OpenData 手動匯入

`scripts/import_plvr_to_postgres.py` 提供受控歷史匯入流程，只處理維護者明確提供的 ZIP、CSV 或資料夾，不會自動下載全台資料。

```text
本機官方 ZIP / CSV
→ 辨識買賣主檔
→ 欄位正規化與品質檢查
→ source + dedupe_key 去重
→ dry-run 審查
→ 寫入 real_price_transactions
→ 記錄 valuation_import_runs
```

正規化包含民國年月、坪數、萬元單價、樓層與路段；品質檢查會排除缺少必要欄位及異常單價。資料夾匯入必須指定城市，超過 10,000 筆需額外確認。`/valuation/data-status` 依資料表實際覆蓋與最近成功匯入紀錄，顯示官方期間、最近匯入範圍與重複筆數。即使已匯入官方資料，只要覆蓋未達全台，仍會明確顯示「尚非完整雙北一年或全台資料」。

## 為什麼不在 Render Runtime 下載

- Render Free 啟動時間有限，大型下載會延後 port 綁定。
- 全台資料量大，清洗與索引會消耗記憶體及 CPU。
- Runtime ETL 會使查詢速度與服務穩定性不可預期。
- 下載或清洗失敗可能直接造成部署失敗。

## 推薦正式架構

```text
Vercel frontend
→ Render FastAPI
→ Supabase Postgres valuation database
→ GitHub Actions updater
```

## 更新頻率

可依官方資料發布節奏，在每月 1、11、21 日之後安排同步。建議排程於每月 2、12、22 日執行，前端顯示 `last_updated`。

## Rolling 3 年逐筆資料策略

官方 PLVR 逐筆交易預設只保留 rolling 3 年。每季更新時先匯入與驗證新資料，再使用 `scripts/prune_valuation_data.py` dry-run 盤點超出保留期間的官方資料，經維護者確認後才可刪除。三年以前若需要長期趨勢，應另建年度或季度統計摘要表，不永久保留全部逐筆交易。

## 安全文案

- 可比成交估算
- 估值區間
- 信心分數
- 估價層級
- 不代表正式鑑價、銀行估價或成交保證
