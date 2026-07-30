# PropTech AI Copilot 競賽展示講稿

## 展示設定

- 主展示 UI：Next.js `http://localhost:3000`
- Backend：FastAPI `http://localhost:8000`
- 備援 UI：Streamlit `http://localhost:8501`
- 展示資料：mock CSV，不串真實政府 API

核心原則：AI 只負責說明，稅務資格由 TX001-TX009 deterministic rule engine 判斷。

## 1 分鐘電梯簡報

「PropTech AI Copilot 是給台灣房仲使用的初步風險溝通工具。主線 TaxOracle 將重購退稅條件整理成 TX001-TX009 規則引擎，輸出資格狀態、risk signal、補件清單與五年列管提醒。AI 不負責判斷資格，只把規則結果改寫成客戶聽得懂的說明。房仲可以一鍵下載 HTML report，並透過 Market Insight Lite 補充區域行情與生活機能。現在版本使用 mock data，目標是先展示一套可解釋、可追蹤、可產品化的房仲工作流程。」

## 3 分鐘正式展示

### 0:00-0:30 定位

「換屋客戶常問：重購退稅是否可能適用、還缺哪些文件、後續有沒有列管風險。房仲需要快速溝通，但不能把初步說明講成正式保證。」

### 0:30-0:55 Next.js 儀表板

「這是產品化 Next.js 後台。競賽展示模式只有三步：選 demo case、執行 TaxOracle 分析、下載 HTML report。」

### 0:55-2:15 TaxOracle

「我先選擇低風險案例。分析結果是 `eligible / green`。頁面顯示 risk signal、Rule Trace、補件清單與五年列管。再切換中風險案例，可以看到 `manual_review / yellow`；高風險案例則是 `not_eligible / red`。」

「這裡最重要的是：資格由 TX001-TX009 deterministic rule engine 判斷，AI 只負責說明。`risk_score` 也只用於排序與展示，不取代法規結論。」

### 2:15-2:40 HTML report

「按下下載按鈕，系統產生 HTML report，包含案件摘要、資格、燈號、Rule Trace、補件、五年 timeline、中文說明與免責聲明。」

### 2:40-3:00 Lite 模組

「Market Insight Lite 提供 mock 區域行情、POI 與 ESG / SDG 11；Aegis-Credit Lite 和 LexProp Lite 也只做展示型風險溝通，不代表正式判斷。」

## 5 分鐘完整展示

### 0:00-0:45 問題場景

「房仲不只是媒合物件，也要處理客戶對稅務、貸款與區域風險的疑問。問題在於資訊分散，而且任何初步溝通都不能被誤解為正式保證。」

### 0:45-1:20 架構

「前端使用 Next.js，backend 使用 FastAPI。FastAPI 直接呼叫既有 Python services、SQLite 與規則引擎，沒有在 frontend 重寫資格邏輯。Streamlit 版本保留作為現場備援。」

### 1:20-3:00 TaxOracle 三案例

「低風險案例 `DEMO-LOW` 為 `eligible / green`。中風險 `DEMO-MEDIUM` 為 `manual_review / yellow`，可看到補件需求。高風險 `DEMO-HIGH` 為 `not_eligible / red`，可看到必要條件失敗。」

「Rule Trace 讓每個結論都可以追溯。AI fallback 只讀 structured result 產生說明，不會修改資格。」

### 3:00-3:35 報告與 History

「分析後可下載 HTML report。結果也會保存到 SQLite，History 頁可檢視案件、客戶、狀態、分數、燈號與建立時間。」

### 3:35-4:25 Market Insight Lite

「Market Insight Lite 延續舊版 OmniUrbanAI v2 的保留概念，但重新做成離線 mock 模組。它提供區域平均單價、六期趨勢、POI 生活機能與 ESG / SDG 11 Lite，不串 TDX、Google Maps、TGOS 或 PLVR 即時資料。」

### 4:25-5:00 收尾

「這個 MVP 的核心不是用 AI 取代專業，而是把房仲的初步溝通流程標準化。下一階段可在治理、授權與版本控管完成後，再逐步串接政府資料。」

## 評審 Q&A

### 為什麼不用 AI 直接判斷稅務？

稅務資格涉及法規責任。TaxOracle 使用可測試、可追蹤的 deterministic rule engine。AI 只改寫 structured result，避免黑盒判斷。

### 為什麼目前使用 mock data？

競賽 MVP 優先驗證產品流程與使用者體驗。真實 API 會引入金鑰、配額、限流、資料授權與版本問題，可能影響現場穩定度。

### 這跟正式報稅系統差在哪？

本系統是房仲與客戶的初步溝通與文件準備工具，不處理正式申報，也不保證資格或稅額。正式結果仍由主管機關與專業人士確認。

### 未來如何串政府資料？

可在 backend service 層加入版本化 adapter，串接授權資料來源，保留 mock fallback、快取、錯誤處理與稽核紀錄。TaxOracle 規則引擎仍維持獨立。

### 如何商業化？

可作為房仲門市 SaaS：提供案件初篩、補件協作、列管提醒、HTML 客戶報告與主管儀表板。進階方案可加入團隊權限、案件 CRM、法規版本管理與正式資料交換。

### 現場如果 Next.js 無法啟動怎麼辦？

保留 `streamlit run app.py` 作為備援展示入口。核心 Python 規則與 mock data 相同。
