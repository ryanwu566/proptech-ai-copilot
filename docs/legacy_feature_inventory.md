# OmniUrbanAI v2 Legacy 功能盤點

## 盤點目的

本文件只做舊專案功能盤點與整合建議，不直接搬移程式碼。

整合原則：

- TaxOracle 仍是競賽展示主線，不被舊功能取代。
- 舊功能只作為補強，不直接複製整包 legacy 專案。
- 第一階段整合不串真實 API、不做登入、不做大型重構。
- 優先以 mock CSV 與可解釋的 deterministic heuristic 建立 `Market Insight Lite`。

## 掃描範圍

### 目前主專案

```text
PropTech AI Copilot/
├─ app.py
├─ backend/
│  ├─ db.py
│  └─ repositories/sqlite_repo.py
├─ data/
│  ├─ mock_tax_cases.csv
│  ├─ mock_buyers.csv
│  ├─ mock_properties.csv
│  ├─ mock_bank_policies.csv
│  ├─ mock_judgments.csv
│  └─ mock_land_values.csv
├─ docs/demo_script.md
├─ models/schemas.py
├─ reports/templates/tax_report.html
├─ rules/
│  ├─ tax_rules.py
│  ├─ mortgage_rules.py
│  └─ legal_risk_rules.py
├─ services/
│  ├─ data_service.py
│  ├─ llm_service.py
│  ├─ report_service.py
│  └─ tax_service.py
└─ tests/
```

### 舊專案

```text
OmniUrbanAI_v2_legacy/
├─ Home.py
├─ pages/
│  ├─ 1_視覺快篩與估價.py
│  ├─ 2_法規虛擬地政士.py
│  ├─ 3_永續與社會責任.py
│  ├─ 4_決策與意願模擬.py
│  └─ 5_總結與報告匯出.py
├─ utils/
│  ├─ engines.py
│  ├─ real_estate_data.py
│  ├─ finance.py
│  ├─ charts.py
│  ├─ geo.py
│  ├─ llm.py
│  ├─ pdf_export.py
│  ├─ data_store.py
│  └─ config.py
├─ scripts/
│  ├─ convert.py
│  └─ new_taiwan_roads.py
├─ data/raw/opendata114road.csv
├─ assets/msjh.ttf
├─ requirements.txt
└─ start.bat
```

## 舊專案頁面與功能

| 頁面 | 主要功能 | 判斷 |
| --- | --- | --- |
| `Home.py` | 地址輸入、縣市行政區路段選擇、估價摘要、歷史價格趨勢、雙地圖、街景、POI 分數、YouBike、公車、捷運、台鐵、自行車道、停車場、天氣、AQI、查詢歷史、實價登錄資料清洗面板 | 功能豐富，但高度依賴外部 API，不適合整包搬移 |
| `1_視覺快篩與估價.py` | 上傳建物照片、人工調整電梯與屋齡、估價因子 waterfall、建物特徵卡片、XAI 式估價說明 | 可保留概念；視覺 AI 目前多為展示邏輯，宜降級成 mock 展示 |
| `2_法規虛擬地政士.py` | 法規聊天、多模型 ensemble、MojLawSplit JSON RAG 搜尋、法條內容擷取、AI 解釋、token 計數 | 與 TaxOracle 的 AI 邊界不同；外部資料與模型依賴高，先不搬 |
| `3_永續與社會責任.py` | ESG 指標、SDG 11 對齊、重建 vs. 整建碳排比較、五維雷達圖、防災韌性、社區包容與高齡友善建議 | 適合拆成 Market Insight Lite 的 mock 指標卡 |
| `4_決策與意願模擬.py` | 都更與危老政策路徑、住戶支持/觀望/反對比例、容積獎勵、權利變換、店面抗性、整合可行性、意願指數、what-if 曲線、策略建議 | 很適合保留為 Lite heuristic，但應避免宣稱正式決策 |
| `5_總結與報告匯出.py` | 匯整估價、法規聊天、ESG 與模擬結果，產生 PDF 報告 | 主專案已有 TaxOracle HTML report；PDF 暫不搬 |

## 功能分類矩陣

| 舊功能 | 值得保留 | 與目前模組重複 | Market Insight Lite 候選 | 需要 mock data | 需要真實 API，先不搬 | 難度 |
| --- | --- | --- | --- | --- | --- | --- |
| 行政區行情摘要與歷史價格趨勢 | 是 | 不重複，可補強 TaxOracle 前後的房市脈絡 | 是 | 是：行政區、月份、平均單價、成交量 | 正式版可接實價登錄下載 | 低 |
| POI 生活機能分數卡 | 是 | 不重複 | 是 | 是：交通、醫療、教育、公園、採買、防災等分數 | 正式版需 TGOS / Google Places | 低 |
| ESG / SDG 11 五維雷達圖 | 是 | 不重複 | 是 | 是：五維分數、碳排比較數字 | 正式版需明確資料來源與計算依據 | 低 |
| 重建 vs. 整建碳排比較 | 是 | 不重複 | 是 | 是：面積、重建碳排、整建碳排 | 正式版需碳排係數治理 | 低 |
| 都更整合意願 what-if 模擬 | 是 | 不重複 | 可作為未來 `Renewal Simulator Lite`，不建議塞入首版 Market Insight Lite | 是：支持率、觀望率、反對率、店面抗性、容積獎勵 | 不需要真實 API，但需清楚標示 heuristic | 中 |
| 地址選擇器與路段清單 | 可保留概念 | 不重複 | 可作為 Market Insight Lite 篩選器 | 是：少量行政區與路段 mock | 全台正式路名維護成本較高 | 低 |
| 視覺快篩與 XAI 估價 waterfall | 可保留概念 | 不重複 | 可延後作為 `Valuation Lite` | 是：建物特徵與調整值 | 真正視覺模型、正式估價資料需另行處理 | 中 |
| 實價登錄下載與清洗 | 清洗邏輯值得保留 | 不重複 | 首版只用離線 mock 結果，不直接下載 | 是：預先整理後的 CSV | `plvr.land.moi.gov.tw` 即時下載先不搬 | 中 |
| 法規 RAG 搜尋與多模型 ensemble | 概念可留 | 與 TaxOracle AI 說明部分重疊，且容易模糊責任邊界 | 否 | 若展示可用離線法條摘要 | MojLawSplit GitHub、LLM provider API | 高 |
| Google Geocode / Street View / Roads | 正式版可能有價值 | 不重複 | 否 | 可用固定 mock 地址與座標替代 | Google Maps API key | 高 |
| TDX 交通即時資訊 | 正式版可能有價值 | 不重複 | 首版只做靜態 mock KPI | 是：YouBike、停車、公車、捷運摘要 | TDX OAuth、限流、各 endpoint 維護 | 高 |
| Open-Meteo 天氣與 AQI | 價值有限 | 不重複 | 非首批 | 是：靜態環境摘要即可 | Open-Meteo 網路請求 | 低 |
| TGOS 地址比對與主題圖資 | 正式版可能有價值 | 不重複 | 否 | 可用固定 POI mock 替代 | TGOS API key 與資料格式 | 高 |
| Folium 雙地圖與 WMTS 圖層 | 視覺效果佳 | 不重複 | 非首批 | 可用靜態圖或資料表替代 | 外部 tile、地理元件與互動狀態 | 中 |
| 舊版 PDF 匯出 | 暫不保留 | 與 TaxOracle HTML report 重複 | 否 | 否 | 字型、Kaleido、PDF 相依較重 | 中 |

## 與目前三個模組的關係

### TaxOracle

目前主專案的 TaxOracle 已有 TX001-TX009 deterministic rule engine、風險燈號、補件、五年列管、fallback 中文說明、SQLite History 與 HTML report。

舊版法規聊天與 RAG 不應取代 TaxOracle，也不應參與資格判斷。若未來保留，只能作為獨立參考資料頁，並明確標示「不會修改 TaxOracle 結論」。

### Aegis-Credit Lite

舊專案沒有等價的房貸風險模組。都更整合意願模擬同樣屬 heuristic，但使用場景不同，不應混入 Aegis-Credit。

### LexProp Lite

舊版法規 RAG 與 LexProp Lite 都涉及法規或風險摘要，但資料來源與責任邊界不同：

- LexProp Lite：匿名化 mock 判決摘要模糊比對。
- 舊版法規 RAG：搜尋法條 JSON，再交由 LLM 解釋。

首批整合不搬法規 RAG，避免讓評審誤以為系統提供正式法律意見。

## Market Insight Lite 建議範圍

建議新增獨立頁面 `Market Insight Lite`，作為 TaxOracle 主線旁的房市脈絡補充，不改動 TaxOracle 規則。

### 首版畫面

1. 選擇 mock 區域或 demo 物件。
2. 顯示區域行情摘要：平均單價、成交量、近六期趨勢。
3. 顯示生活機能分數卡：交通、醫療、教育、公園、防災。
4. 顯示 ESG / SDG 11 Lite：五維分數與重建 vs. 整建碳排示意。
5. 固定提示：「展示版 mock data，不構成估價、投資或都更決策建議。」

### 建議 mock data

可新增：

```text
data/mock_market_insights.csv
data/mock_price_trends.csv
data/mock_poi_scores.csv
data/mock_esg_scores.csv
```

## 需要真實 API 的功能：先不要搬

| API 或外部來源 | 舊用途 | 暫緩原因 |
| --- | --- | --- |
| TDX OAuth 與交通 API | YouBike、公車、捷運、台鐵、自行車道、停車場 | 需要 client credentials、限流處理與 endpoint 維護 |
| Google Maps API | Geocode、Reverse Geocode、Street View、Places、Roads | 需要 API key、費用與配額管理 |
| TGOS API | 地址比對、主題圖資、WMTS | 需要 key、格式驗證與正式資料治理 |
| Open-Meteo | 天氣、AQI | 可展示但非 TaxOracle 主線，首批效益有限 |
| 內政部實價登錄下載 | 真實成交資料下載與清洗 | 首版改用離線 mock CSV，避免網路失敗影響展示 |
| MojLawSplit GitHub JSON | 法規索引與法條內容 | 依賴外部網路；法規版本與法律責任需另行治理 |
| Groq、Gemini、GitHub Models、Cohere、OpenRouter、SambaNova、Cerebras | 多模型法規聊天與 ensemble | 金鑰多、成本與輸出不穩定，不符合離線展示需求 |

## 建議第一批整合功能

### 1. 區域行情摘要與六期趨勢

- 新頁面：`Market Insight Lite`
- 資料：離線 mock CSV
- 呈現：KPI cards、簡單折線圖、成交量
- 理由：最容易理解，能補充 TaxOracle 使用場景，整合難度低。

### 2. 生活機能分數卡

- 新頁面：`Market Insight Lite`
- 資料：離線 POI mock CSV
- 呈現：交通、醫療、教育、公園、防災五項分數
- 理由：保留 OmniUrban 的都市機能特色，不需要地圖或真實 API。

### 3. ESG / SDG 11 Lite 指標

- 新頁面：`Market Insight Lite`
- 資料：離線 ESG mock CSV
- 呈現：五維分數、雷達圖、重建 vs. 整建碳排示意
- 理由：競賽辨識度高，可與房仲服務定位形成差異化，仍可保持離線穩定。

## 第二批候選

- `Renewal Simulator Lite`：保留都更整合意願、容積獎勵與觀望戶轉化 what-if，但必須標示為展示型 heuristic。
- `Valuation Lite`：保留估價 waterfall 的可解釋視覺，但只使用 mock 特徵，不宣稱正式估價。
- 靜態交通與環境摘要：只放 mock KPI，不直接串 TDX、Google 或 TGOS。

## 主要風險

1. **字元編碼風險**：legacy 部分繁體中文字串在目前環境顯示失真。整合時應重新整理文案，不直接複製頁面檔案。
2. **高耦合風險**：`Home.py` 與 `utils/engines.py` 將 session state、UI、API、地圖與估價流程緊密綁定。應抽取概念與資料欄位，不直接搬 class。
3. **外部 API 穩定性風險**：TDX、Google、TGOS、PLVR 與 MojLawSplit 均可能受金鑰、配額、限流或網路影響，不適合競賽主展示。
4. **責任邊界風險**：舊版法規聊天、多模型 ensemble、估價與都更成功率容易被誤解為正式判斷。Lite 頁面必須顯示免責說明。
5. **相依套件風險**：legacy 使用 `folium`、`streamlit-folium`、`plotly`、`kaleido`、`fpdf2`、`openai` 等額外套件。第一批整合只引入真正需要的圖表套件。
6. **資料治理風險**：ESG、POI、碳排與估價分數若未標示來源，容易被評審追問。mock 指標需清楚標示為示意資料。

## 結論

舊專案值得保留的是「都市機能脈絡、ESG 差異化、都更 what-if」三類概念，而不是整包搬移。第一批應只新增 `Market Insight Lite`，使用 mock CSV 提供區域行情、生活機能與 ESG / SDG 11 Lite，讓 TaxOracle 仍然保持最清楚、最穩定的競賽主線。

## 第四階段整合狀態

第一批整合已完成，採用獨立重做方式，沒有直接複製 legacy 頁面或 `utils/engines.py`。

| 第一批項目 | 狀態 | 實作方式 |
| --- | --- | --- |
| 區域行情摘要與六期趨勢 | 已完成 | `Market Insight Lite` 頁面讀取 `data/mock_market_insights.csv` |
| POI 生活機能分數卡 | 已完成 | service 產生交通、教育、公園、醫療與綜合機能分數 |
| ESG / SDG 11 Lite 指標 | 已完成 | service 計算 bounded ESG Lite 分數並顯示 SDG 11 mock 說明 |

新增檔案：

```text
data/mock_market_insights.csv
services/market_insight_service.py
tests/test_market_insight_service.py
```

### 仍暫不整合

| 暫緩項目 | 保留理由 |
| --- | --- |
| TDX 即時交通 | 需要 OAuth、限流處理與 endpoint 維護，不適合離線競賽主流程 |
| Google Maps / TGOS | 需要 API key、配額與地理資料治理 |
| PLVR 即時下載 | 網路失敗可能影響展示，首版改用離線 mock CSV |
| 法規 RAG 與多模型 ensemble | 容易模糊 TaxOracle deterministic rule engine 的責任邊界 |
| PDF 匯出 | 主專案已提供穩定的 TaxOracle HTML report |
| 登入與大型重構 | 不屬於本階段競賽展示需求 |
