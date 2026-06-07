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

1. `VALUATION_DATABASE_URL` 對應的 Postgres provider placeholder
2. `data/processed/valuation_index.sqlite`
3. `data/real_price_sample.csv`
4. 記憶體展示資料 fallback

Provider 在第一次呼叫估價或資料狀態 API 時才初始化。`/health` 不讀取估價資料。

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

## 安全文案

- 可比成交估算
- 估值區間
- 信心分數
- 估價層級
- 不代表正式鑑價、銀行估價或成交保證
