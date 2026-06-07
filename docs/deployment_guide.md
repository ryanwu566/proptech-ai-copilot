# Deployment Guide

推薦部署架構：

- FastAPI backend：Render
- Next.js frontend：Vercel
- Source：`https://github.com/ryanwu566/proptech-ai-copilot`

目前系統使用 mock data；SQLite 在 Render 免費 Web Service 的檔案系統上不保證永久保存。重新部署或服務重建後，歷史案件可能重置。

## A. Render 後端部署

1. 在 Render 建立 **New Web Service**，連接 GitHub repo。
2. Root Directory 保持 repo root，或留白。
3. Build Command：

   ```text
   pip install -r requirements.txt
   ```

4. Start Command：

   ```text
   uvicorn backend.api_main:app --host 0.0.0.0 --port $PORT
   ```

5. 設定環境變數：

   ```text
   CORS_ORIGINS=https://你的-vercel-domain.vercel.app
   ```

   如需啟用 Map Insight 的 Google Places 周遭生活機能查詢，在 Render backend 設定：

   ```text
   GOOGLE_MAPS_API_KEY
   ```

   未設定或 Google Geocoding / Places 發生 timeout、quota、服務錯誤時，backend 會自動使用 mock fallback。Map Insight 仍可展示生活機能分數拆解、最近設施、POI 清單與客戶說明建議。
   設定後可用 `GET /map/google-health` 確認 Google Geocoding 與 Places 是否真的啟用；回應不會包含 API key。

   以下真實 API adapter 尚未啟用，可留空或不設定：

   ```text
   TDX_CLIENT_ID
   TDX_CLIENT_SECRET
   TGOS_API_KEY
   ```

6. 部署完成後開啟：

   ```text
   https://你的-render-backend.onrender.com/health
   ```

   應回傳 `status: ok`。

`CORS_ORIGINS` 支援逗號分隔多個來源。未設定時，backend 僅預設允許 `http://localhost:3000` 與 `http://127.0.0.1:3000`。

## B. Vercel 前端部署

1. 在 Vercel 選擇 **Import Git Repository**。
2. 選擇 GitHub repo。
3. Root Directory 設為：

   ```text
   frontend_next
   ```

4. Framework Preset 選擇 **Next.js**。
5. Build Command：

   ```text
   npm run build
   ```

6. 設定環境變數：

   ```text
   NEXT_PUBLIC_API_BASE_URL=https://你的-render-backend.onrender.com
   ```

   Vercel 不需要且不應設定 `GOOGLE_MAPS_API_KEY`；Google Places 只能由 Render backend 呼叫。
   請勿將 `GOOGLE_MAPS_API_KEY` 設在 Vercel 或任何 `NEXT_PUBLIC_` 變數中。
   Map Insight 的 OpenStreetMap、CartoDB Positron 與 Esri World Imagery 圖層不需要前端 Google key。
   `data/taiwan_roads.csv` 會隨專案部署，提供縣市／鄉鎮市區／路段快速選擇，不依賴 OneDrive 或外部路名 API。
   Aegis-Credit 的市場房貸利率參考會由 Render backend 呼叫中央銀行 OpenData，不需要 API key；若外部 API 暫時無法使用，會自動使用展示資料 fallback。
   銀行牌告利率查詢使用中央銀行 OpenData `set_id=9464`，不需要 API key；房價估算使用隨專案部署的 `data/real_price_sample.csv`，不會在啟動時下載全台資料。

7. 部署後開啟首頁，測試 TaxOracle 三個案例、客戶溝通報告下載與 Map Insight 周遭生活機能查詢。

## C. 常見錯誤

### CORS blocked

- 確認 Render 的 `CORS_ORIGINS` 完整包含 Vercel 網域，且沒有多餘路徑。
- 修改環境變數後重新部署 Render。

### Render backend sleeping / first request slow

- Render 免費服務休眠後，第一次請求可能需要較長時間。
- 先開啟 `/health` 喚醒服務，再操作前端。

### NEXT_PUBLIC_API_BASE_URL 設錯

- 必須是 Render backend 的公開 HTTPS 網址。
- 修改後需重新部署 Vercel，因為 `NEXT_PUBLIC_` 變數會寫入 frontend build。

### Data file not found

- 確認 `data/mock_tax_cases.csv`、`data/mock_map_points.json` 與其他 mock CSV 已提交至 GitHub。
- Render Root Directory 必須是 repo root 或留白。

### npm build failed

- 確認 Vercel Root Directory 是 `frontend_next`。
- 本機先執行 `npm.cmd --prefix frontend_next run build`。

### Python dependency missing

- 確認套件已列在 repo root 的 `requirements.txt`。
- Render Build Command 必須使用 `pip install -r requirements.txt`。
## 資料服務環境變數

Render backend 可設定 `GOOGLE_MAPS_API_KEY`、`TGOS_APP_ID`、`TGOS_API_KEY`。三者都不可放在 Vercel 或 commit 到 repo。

定位會依序嘗試 Google Geocoding、TGOS，最後使用展示資料。沒有 key 或外部服務失敗時，系統會安全 fallback，不影響 TaxOracle。

銀行牌告利率使用中央銀行 OpenData `set_id=9464`，不需要 API key。房價估算目前使用 `real_price_sample.csv`，PLVR adapter 尚未啟用。

### 房價估算資料庫

目前不需要設定 `VALUATION_DATABASE_URL`，系統會使用 sample provider。切換 Supabase/Postgres 時，只能在 Render backend 設定此變數；Vercel 不需要。若資料庫不可用，系統會安全 fallback 至 SQLite、sample 或展示資料。

不要在 Render start command 或 runtime 執行 `scripts/update_valuation_data.py`。大型資料更新應由 GitHub Actions 或獨立後台排程執行。
