# 最終展示檢查清單

## 展示前 10 分鐘

- 使用兩個 PowerShell 視窗，分別啟動 backend 與 frontend。
- 開啟 `http://localhost:3000`，確認 Dashboard 可載入。
- 執行 `powershell -ExecutionPolicy Bypass -File .\scripts\check_demo.ps1`。
- 預先跑過 TaxOracle 三個 demo case，確認燈號與說明文字。
- 下載一次 HTML report，確認瀏覽器可正常開啟。
- 開啟 Map Insight Lite，確認 mock 地址可定位並顯示 POI 圖層。
- 關閉不必要的程式與通知，保留展示所需分頁。

## 後端啟動檢查

```powershell
.\scripts\start_backend.ps1
```

瀏覽器開啟 `http://localhost:8000/health`，應看到 `status` 為 `ok`。

## 前端啟動檢查

另開 PowerShell 視窗：

```powershell
.\scripts\start_frontend.ps1
```

瀏覽器開啟 `http://localhost:3000`，應顯示 Next.js SaaS 後台首頁。

## TaxOracle 三案例檢查

| Demo case | 預期資格 | 預期燈號 |
| --- | --- | --- |
| `DEMO-LOW` | `eligible` | `green` |
| `DEMO-MEDIUM` | `manual_review` | `yellow` |
| `DEMO-HIGH` | `not_eligible` | `red` |

確認每個案例都能顯示 Rule Trace、缺件清單、五年列管提醒與中文說明。

## HTML Report 下載檢查

- 在 TaxOracle 結果頁點擊下載 HTML report。
- 確認報告包含案件摘要、資格結果、風險燈號、Rule Trace、補件清單、五年列管、中文說明與免責聲明。
- 本 MVP 不提供 PDF。

## Map Insight Lite 檢查

- 搜尋 `台北市大安區和平東路二段`，確認地圖中心點與 POI markers 顯示。
- 確認分類 pills 顯示數量，切換後 marker 與右側清單同步過濾。
- 確認右側顯示生活機能分數拆解、最近設施與客戶說明建議。
- 點選一筆 POI 地點卡，確認地圖聚焦並開啟 marker popup。
- 確認資料來源顯示 Google Places 或 Mock fallback；未設 key 時應正常使用展示資料。
- 切換交通、學校、公園、醫療、商圈分類。
- 確認畫面標示 Mock Data 與免責聲明。
- 真實 Google、TGOS、TDX、PLVR adapter 尚未啟用；現場不需要 API key。

## Aegis-Credit Lite 檢查

- 確認市場房貸利率參考顯示資料期間、參考利率、來源與更新時間。
- 清楚說明中央銀行 OpenData 為五大銀行月資料，不是即時或實際核貸利率。
- 若顯示「展示資料 fallback」，確認房貸風險分析仍可正常執行。
- 提醒實際利率仍依銀行審核、信用條件、擔保品、收入、負債比與方案而定。
- 切換銀行 dropdown，確認牌告利率項目、生效日期與資料來源正常顯示。

## 房價估算檢查

- 選擇縣市、鄉鎮市區、路段與物件條件後執行估算。
- 確認顯示估算總價、每坪單價、估值區間、信心分數與可比成交。
- 清楚說明目前使用 sample data，結果不是正式鑑價、銀行估價、成交保證或投資建議。

## 常見問題

### Backend 沒開

執行：

```powershell
.\scripts\start_backend.ps1
```

### Port 3000 或 8000 被占用

先找出占用程序：

```powershell
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 3000,8000 }
```

關閉不需要的舊程序後重新啟動。展示前不要臨時修改前端 API port。

### npm install 失敗

確認 Node.js 與 npm 可用，再於 `frontend_next` 執行：

```powershell
npm.cmd install
```

若現場網路不穩，優先使用已安裝完成的本機環境。

## 展示提醒

- 主線只講 TaxOracle：資格快篩、Rule Trace、五年列管與 HTML report。
- 清楚說明 AI 只負責將結構化結果改寫成說明，資格由 deterministic rule engine 判斷。
- 清楚說明目前使用 mock data，不是正式報稅、法律、估價或核貸系統。
- Lite 模組快速帶過即可，不要花太多時間談尚未完成的擴充功能。
