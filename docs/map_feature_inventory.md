# Omni Urban AI 地圖功能盤點

## 盤點範圍與結論

本文件只做 legacy 地圖功能盤點與整合建議，不直接搬移舊程式。

- 正式工作目錄：`C:\Projects\proptech-ai-copilot`
- 唯讀 legacy 來源：`C:\Users\吳奕陽\OneDrive\文件\OmniUrbanAI_v2_legacy`
- 掃描結果：已成功讀取真正的 Omni Urban AI v2 Python / Streamlit 原始碼。
- 本次未修改 legacy 來源，也未複製任何 legacy 頁面、API key 或敏感設定到正式專案。

已確認 legacy 具備：

```text
OmniUrbanAI_v2_legacy/
├─ Home.py
├─ pages/
│  ├─ 1_👁️_視覺快篩與估價.py
│  ├─ 2_📜_法規虛擬地政士.py
│  ├─ 3_🌍_永續與社會責任.py
│  ├─ 4_🎯_決策與意願模擬.py
│  └─ 5_📑_總結與報告匯出.py
├─ utils/
│  ├─ geo.py
│  ├─ engines.py
│  ├─ real_estate_data.py
│  ├─ config.py
│  └─ data_store.py
├─ scripts/
│  ├─ convert.py
│  └─ new_taiwan_roads.py
├─ data/raw/opendata114road.csv
├─ .streamlit/secrets.toml
└─ requirements.txt
```

## 整合原則

- TaxOracle 維持正式專案主線，不修改核心規則或既有 API。
- Map Insight / Geo Map Lite 僅作為補充模組。
- 不直接搬舊 Streamlit / Folium 頁面進 Next.js。
- FastAPI 管理 API adapter、金鑰、快取、正規化與 mock fallback。
- Next.js 管理地圖互動、marker、圖層控制與資訊卡。
- 沒有 API key 或外部服務異常時，必須回傳相同 schema 的 mock data。
- `.env`、`.env.local`、`secrets.toml` 不可 commit。

## 1. 舊專案地圖功能清單

| 功能 | 實際用途 | Legacy 實作位置 |
| --- | --- | --- |
| 地址輸入與縣市 / 行政區 / 路段選擇 | 可手動輸入完整地址，或從全台路段資料建立地址 | `Home.py`、`OmniEngine.get_roads_list()`、`utils/data_store.py` |
| 地址 Geocoding | TGOS 地址比對優先，Google Geocoding 備援；無結果時回固定預設座標 | `utils/geo.py:get_tgos_coordinates()`、`utils/engines.py:get_dynamic_data()` |
| Reverse Geocoding | 點擊地圖後以 Google Geocoding 反查地址，重新執行分析 | `Home.py`、`utils/engines.py:reverse_geocode()` |
| Folium 雙地圖 | 使用 `folium.plugins.DualMap` 同步顯示左右地圖 | `Home.py`、`utils/engines.py:create_dual_map()` |
| 地圖點擊重新定位 | 使用者點擊地圖任意位置，反查新地址並同步街景與分析 | `Home.py` |
| 地圖圖層控制 | OSM、CartoDB、Esri 衛星、NLSC 地籍圖、土地使用圖、TGOS WMTS | `utils/engines.py:create_dual_map()` |
| 800m 分析範圍 | 在雙地圖繪製矩形分析範圍與基地 marker | `utils/engines.py:create_dual_map()` |
| POI marker | 顯示交通、醫療、教育、商業、綠地、防災等周邊點位 | `utils/engines.py:get_real_poi_scores()`、`create_dual_map()` |
| TGOS 主題圖資 | 查詢周邊主題資料，分類為使用分區、敏感設施、嫌惡設施等 | `utils/geo.py` |
| Google Street View | 以 iframe 顯示基地街景，並依 Google Roads 計算 heading | `Home.py`、`utils/engines.py:_get_street_heading()` |
| TDX YouBike | 查詢附近站點與即時可借 / 可還數量 | `utils/engines.py:get_youbike_data()` |
| TDX 公車與捷運 | 查詢附近站點、到站時間、捷運與台鐵點位 | `utils/engines.py:get_bus_data()`、`_count_tdx_transit_points()` |
| TDX 自行車道 | 查詢附近自行車道，Google Places 作備援 | `utils/engines.py:get_bike_lanes()` |
| TDX 停車場 | 查詢附近停車場與即時剩餘格位 | `utils/engines.py:get_parking_data()` |
| TDX 台鐵延誤 | 顯示列車即時延誤資訊 | `utils/engines.py:get_train_delay_data()` |
| 天氣與 AQI | 取得基地即時溫度、濕度與美國 AQI | `utils/engines.py:get_weather_data()`、`get_environmental_data()` |
| PLVR 實價登錄 | 下載與清洗實價登錄資料，作為區域 / 路段行情基礎 | `utils/real_estate_data.py`、`Home.py:render_plvr_cleaner_panel()` |
| 查詢歷史 | 保存已分析地址與地圖結果，供重新載入 | `Home.py`、legacy session state |

## 2. 對應舊檔案位置與責任

| 舊檔案 | 地圖責任 | 整合判斷 |
| --- | --- | --- |
| `Home.py` | 所有地圖 UI、地址表單、雙地圖、點擊事件、街景、交通看板與診斷面板 | 不直接搬；拆成 Next.js 頁面與元件 |
| `utils/geo.py` | TGOS 地址比對、TGOS 主題資料、feature 正規化與分類 | 可改寫為 FastAPI adapter / service |
| `utils/engines.py` | 聚合 Google、TGOS、TDX、Open-Meteo、POI、地圖圖層與估價流程 | 不整包搬；逐個拆 adapter |
| `utils/real_estate_data.py` | PLVR 下載、CSV 清洗、行政區篩選、真實單價計算 | 可拆為獨立 FastAPI data adapter |
| `utils/config.py` | 城市代碼、TDX 縣市對照、捷運系統、預設座標、PLVR 城市代碼 | 可抽取非敏感常數 |
| `utils/data_store.py` | Streamlit session state 與跨頁資料 | 不搬；改用 React state / FastAPI / SQLite |
| `scripts/convert.py` | 將 `opendata114road.csv` 轉為 Python 路名字典 | 可改成離線資料產製腳本 |
| `scripts/new_taiwan_roads.py` | 生成後的全台路名字典 | 不直接載入前端；首批使用小型 mock |
| `data/raw/opendata114road.csv` | 全台縣市、行政區、路名資料 | 已找到；適合離線加工，不適合直接送到瀏覽器 |
| `pages/1_👁️_視覺快篩與估價.py` | 消費地址與 POI 分數，不直接建立地圖 | 不屬首批地圖整合 |
| `pages/3_🌍_永續與社會責任.py` | 消費 POI 與防災分數 | 可作未來地圖摘要卡 |
| `pages/4_🎯_決策與意願模擬.py` | 消費座標與 POI / 防災分數 | 不屬首批地圖整合 |
| `pages/5_📑_總結與報告匯出.py` | 報告中顯示地址、座標與 TGOS 說明 | 不搬 PDF；可保留資料欄位概念 |

### 路名資料確認

`data/raw/opendata114road.csv` 已找到：

- 欄位：`city,site_id,road`
- 約 35,523 行
- 約 1.46 MB

首批不建議將完整 CSV 直接載入 Next.js；應由 FastAPI 提供搜尋 endpoint，或產生小型 mock 路段清單。

## 3. Folium 與圖層盤點

Legacy `requirements.txt` 明確使用：

```text
folium
streamlit-folium
```

`create_dual_map()` 使用 `folium.plugins.DualMap`，包含：

- OpenStreetMap
- CartoDB Positron
- Esri World Imagery
- NLSC WMTS 地籍圖
- NLSC WMTS 土地使用圖
- TGOS 官方底圖 WMTS
- POI marker
- 基地 marker
- 800m 分析範圍
- LayerControl

### Next.js 改寫建議

首批建議使用 **React Leaflet**：

- Folium 與 React Leaflet 都以 Leaflet 為基礎，概念遷移成本最低。
- 可用 `dynamic import` 關閉 SSR，避免瀏覽器物件錯誤。
- 適合 marker、rectangle、tile layer、layer control 與 popup。

若未來需要大量向量圖層、GeoJSON 樣式與更複雜圖層管理，再評估 MapLibre。

## 4. API 與外部服務盤點

| API / 來源 | Legacy 用途 | 實際位置 | 首批建議 |
| --- | --- | --- | --- |
| TGOS 地址比對 | 地址轉座標 | `utils/geo.py:get_tgos_coordinates()` | 建立 `GeocodingAdapter`，預設 mock |
| TGOS 主題資料 | 周邊設施與主題分類 | `utils/geo.py:fetch_tgos_theme_data()`、`get_advanced_tgos_theme_data()` | 建立 `ThemeAdapter`，暫不啟用真實 API |
| TGOS WMTS | 官方底圖 | `utils/engines.py:create_dual_map()` | 暫緩，先確認授權與瀏覽器使用方式 |
| Google Geocoding | 地址轉座標、反向地址 | `utils/engines.py:get_dynamic_data()`、`reverse_geocode()` | 建立 Google adapter，沒有 key 時 fallback |
| Google Places | 公車備援、POI、步道備援 | `utils/engines.py` | 建立 `PoiAdapter`，首批 mock |
| Google Roads | 計算 Street View heading | `utils/engines.py:_get_street_heading()` | 暫緩 |
| Google Street View Embed | 顯示基地街景 | `Home.py` | 暫緩 |
| TDX OAuth | 取得交通 API token | `utils/engines.py:_get_tdx_token()` | 建立 backend token client，不可放前端 |
| TDX Bike | YouBike 站點與可用車位 | `utils/engines.py:get_youbike_data()` | 首批 mock |
| TDX Bus / Rail / Metro | 公車、捷運、台鐵站點與動態 | `get_bus_data()`、`_count_tdx_transit_points()` | 首批 mock |
| TDX Cycling | 自行車道 | `get_bike_lanes()` | 首批 mock |
| TDX Parking | 停車場與可用格位 | `get_parking_data()` | 首批 mock |
| TDX Train Delay | 台鐵延誤 | `get_train_delay_data()` | 暫緩 |
| PLVR | 實價登錄下載與清洗 | `utils/real_estate_data.py` | 使用既有 Market Insight mock |
| Open-Meteo | 天氣、濕度與 AQI | `utils/engines.py` | optional adapter，非首批 |
| NLSC WMTS | 地籍圖與土地使用圖 | `create_dual_map()` | 暫緩，確認授權與 CORS |
| Esri tile | 衛星空照圖 | `create_dual_map()` | 非必要圖層 |

## 5. 建議 API Adapter

| Adapter | Legacy 對應 | 正式版責任 |
| --- | --- | --- |
| `GeocodingAdapter` | TGOS / Google Geocoding / Reverse Geocoding | 地址與座標轉換、fallback、來源標記 |
| `ThemeLayerAdapter` | TGOS 主題資料、TGOS / NLSC WMTS | 正規化主題資料與圖層 metadata |
| `PoiAdapter` | TGOS 主題資料、Google Places | POI 分類、marker、距離與摘要 |
| `TrafficAdapter` | TDX Bike / Bus / Rail / Metro / Cycling / Parking | OAuth、快取、限流與統一 schema |
| `RealEstateAdapter` | PLVR | 行情下載、清洗、快取與 mock fallback |
| `EnvironmentAdapter` | Open-Meteo | 天氣與 AQI；非首批 |
| `RoadDirectoryRepository` | `opendata114road.csv` / `new_taiwan_roads.py` | 路段搜尋與行政區篩選 |

不要直接搬 `OmniEngine`；它同時負責 session、API、估價、地圖與 UI 資料，耦合過高。

## 6. 環境變數盤點

### Legacy 實際使用的地圖 / 交通相關 secrets

程式碼實際引用：

```dotenv
GOOGLE_MAPS_API_KEY=
TDX_CLIENT_ID=
TDX_CLIENT_SECRET=
TGOS_APPID=
TGOS_APIKEY=
TGOS_THEME_KEY=
TGOS_THEME_APIKEY=
TGOS_MAP_KEY=
```

Legacy `.streamlit/secrets.toml` 中另發現下列地圖相關名稱：

```dotenv
GOOGLE_MAPS_API_KEY=
MAPBOX_API_KEY=
CWA_KEY=
TDX_CLIENT_ID=
TDX_CLIENT_SECRET=
TGOS_ADDR_APPID=
TGOS_ADDR_APIKEY=
TGOS_MAP_APIKEY=
TGOS_THEME_APIKEY=
```

### 命名風險

TGOS 命名不一致：

- 程式碼：`TGOS_APPID`、`TGOS_APIKEY`、`TGOS_THEME_KEY`、`TGOS_MAP_KEY`
- secrets 檔：`TGOS_ADDR_APPID`、`TGOS_ADDR_APIKEY`、`TGOS_THEME_APIKEY`、`TGOS_MAP_APIKEY`

正式版整合前應統一命名，例如：

```dotenv
TGOS_ADDR_APP_ID=
TGOS_ADDR_API_KEY=
TGOS_THEME_API_KEY=
TGOS_MAP_API_KEY=
```

所有 key 都只能由 FastAPI backend 讀取，不得使用 `NEXT_PUBLIC_`。

## 7. 可改成 FastAPI Adapter 的功能

1. 地址 Geocoding / Reverse Geocoding
2. TGOS 主題資料查詢與分類
3. Google Places / TGOS POI 查詢
4. TDX OAuth、YouBike、公車、捷運、台鐵、自行車道與停車場
5. PLVR 下載與清洗
6. Open-Meteo 天氣與 AQI
7. 全台路名資料搜尋
8. 地圖圖層設定與來源 metadata

FastAPI 回傳建議統一包含：

```json
{
  "source": "mock | tgos | google | tdx | plvr",
  "is_fallback": true,
  "fallback_reason": "",
  "data_updated_at": "",
  "items": []
}
```

## 8. 可改成 Next.js 地圖元件的功能

| Legacy UI | Next.js 元件建議 |
| --- | --- |
| Folium DualMap | `geo-map.tsx`；首批先做單地圖，雙地圖延後 |
| LayerControl | `map-layer-control.tsx` |
| POI marker | `poi-marker-layer.tsx` |
| 800m 範圍 | `analysis-radius.tsx` |
| 地圖點擊重新定位 | `map-click-handler.tsx` |
| 地址 / 路段輸入 | `location-search.tsx` |
| 交通資訊列 | `mobility-summary.tsx` |
| 圖層圖例 | `map-legend.tsx` |
| API 診斷面板 | 不直接搬；改成簡潔資料來源 badge |

Street View、Google Roads 與 WMTS 圖層不建議進入第一批。

## 9. 先使用 Mock Fallback 的功能

- 五個既有 Market Insight 區域中心點。
- 每區匿名化 POI marker：交通、醫療、教育、公園、採買。
- 行政區與少量路段搜尋。
- YouBike、公車、捷運與停車摘要。
- 800m 分析範圍。
- 行情摘要與六期趨勢。
- API 來源與 fallback 狀態。

沒有 key 時，前端仍應完整顯示地圖與 mock 資料，不顯示錯誤白畫面。

## 10. 高風險、暫緩功能

| 功能 | 暫緩原因 |
| --- | --- |
| Google Street View | 費用、配額、授權與 key 管理 |
| Google Roads | 首批價值有限，額外費用與複雜度高 |
| TGOS / NLSC WMTS | 需確認授權、CORS、tile 格式與瀏覽器使用方式 |
| TDX 全套即時資料 | OAuth、限流、endpoint 差異與展示穩定性 |
| PLVR 即時下載 | 來源格式與網路失敗風險 |
| 全台路名 CSV 直接送前端 | 資料量與搜尋效能不佳 |
| Folium HTML 直接嵌入 Next.js | 狀態與樣式難維護 |
| Legacy API 診斷面板 | 過度工程化，不符合正式 SaaS UI |

## 11. 建議第一批實作的三個地圖功能

### 1. Market Insight 區域定位地圖

- 使用目前五筆 `mock_market_insights.csv`。
- 為每區補固定中心座標。
- 地圖旁顯示平均單價、交易量、生活機能與 ESG 分數。
- 理由：重用既有正式資料，整合風險最低。

### 2. Mock POI 分類圖層

- 顯示交通、醫療、教育、公園、採買匿名化 marker。
- 提供分類切換與 POI 摘要。
- 理由：保留 Omni Urban AI 最有辨識度的地圖能力，不需 API key。

### 3. Mock 地址 / 路段搜尋與定位

- 先從 `opendata114road.csv` 產生少量展示路段資料。
- 搜尋後定位地圖並顯示所屬 Market Insight 區域。
- 理由：建立未來 Geocoding adapter 的操作流程，同時維持離線展示穩定。

## 12. 建議正式專案結構

```text
backend/
  api/
    routes_map.py
  adapters/
    geocoding_adapter.py
    poi_adapter.py
    traffic_adapter.py
    map_layer_adapter.py
    real_estate_adapter.py
  services/
    map_insight_service.py

data/
  mock_map_regions.csv
  mock_map_pois.csv
  mock_map_roads.csv

frontend_next/
  components/
    map/
      geo-map.tsx
      location-search.tsx
      map-layer-control.tsx
      map-legend.tsx
      poi-marker-layer.tsx
      mobility-summary.tsx

tests/
  test_map_insight_service.py
  test_map_api.py
```

## 13. 敏感檔案與安全檢查

- 發現敏感設定檔：`.streamlit/secrets.toml`
- Legacy `.gitignore` 已明確排除 `.streamlit/secrets.toml`
- 以安全方式檢查後，確認該 secrets 檔未被 legacy Git 追蹤
- 未輸出任何 secrets 值
- Python 程式掃描發現 `utils/engines.py` 有 `TGOS_THEME_APIKEY` 的文件範例 placeholder；未發現可確認的真實 key 硬寫
- Legacy Git 工作樹本身有既有變更與未追蹤檔案；本次未修改或清理

除地圖服務外，secrets 檔還包含多個 LLM provider key 名稱；它們不屬於地圖整合，也不應搬入正式專案。

## 下一步實作建議

第一批實作不需要使用者提供任何 API key：

1. 新增 mock 地區中心點、POI 與展示路段資料。
2. 建立 FastAPI `map-insights` mock service 與固定 schema。
3. 在 Next.js 新增 React Leaflet 單地圖與 POI 分類切換。
4. 確認沒有 key 時仍能完成完整展示。

第二批才建立真實 adapter，優先順序建議為：

1. TGOS 或 Google Geocoding 二選一。
2. TDX 單一交通類別，例如 YouBike。
3. 其他 POI、交通與 WMTS 圖層。

任何真實 API 上線前，都應先補快取、限流、timeout、錯誤處理、來源標示與 mock fallback。

## 第一批實作狀態

Map Insight Lite 第一批 mock 版已完成：

- FastAPI endpoints：`GET /map/regions`、`GET /map/poi-categories`、`POST /map/search`、`POST /map/insight`
- Mock-first adapters：Geocoding、POI、Traffic
- Next.js React Leaflet 地圖、中心點、800m 範圍、POI 分類切換與 marker 清單
- Mock 地址 / 路段搜尋：大安區和平東路二段、板橋區文化路二段、信義區松仁路

## Google Places 周遭生活機能整合狀態

正式專案已新增 backend-only Google Places (New) adapter 與 `POST /map/nearby`：

- 類別：交通、學校、公園、醫療、商圈、餐飲。
- 只由 Render backend 讀取 `GOOGLE_MAPS_API_KEY`，前端不接觸 key。
- 使用 field mask 取得名稱、位置、地址、評分、評分數、營業狀態與類型。
- backend 正規化資料、計算距離與生活機能分數後才回傳前端。
- 同一查詢使用簡單 in-memory cache。
- 缺 key、timeout、quota 或 Google 服務錯誤時自動回傳 mock fallback。
- Google Geocoding 已改為有 key 時優先使用；若失敗才 fallback mock，前端會清楚區分定位來源與 POI 來源。

## Map Insight v3 狀態

- 新增 `GET /map/google-health`，以五分鐘 process-level cache 檢查 Google Geocoding 與 Places，且不回傳或輸出 API key。
- `/map/search` 回傳 `formatted_address`、`place_id`、`confidence` 與 `location_note`，避免將展示定位誤認為 Google 定位。
- 前端底圖可切換 OpenStreetMap、CartoDB Positron 與 Esri World Imagery；不使用 Google Maps tiles。
- `/map/nearby` 回傳 `scoring_criteria`，公開交通 25%、餐飲 20%、商圈 20%、學校 15%、醫療 10%、公園 10% 的類別權重，以及 0–300m、300–800m、800m 外的距離級距。
- Render backend 設定 `GOOGLE_MAPS_API_KEY` 才會啟用 Google；Vercel 不需要且不應設定此 key。

## Map Insight v5 狀態

- 從舊版 `opendata114road.csv` 整理出正式專案內的 `data/taiwan_roads.csv`，部署後不依賴 OneDrive。
- 新增 `/roads/cities`、`/roads/districts`、`/roads/roads`，支援快速選擇縣市、鄉鎮市區與路段；找不到資料時回傳空陣列與友善訊息。
- 前端預設使用快速選擇，也保留完整地址或路段手動輸入。
- `/map/nearby` 新增生活機能五級總評，並將六類 `category_scores` 統一為指標陣列；每項包含權重、分數、等級、POI 數量、最近距離與解釋。
- POI 清單依分類分組，優先依距離、評分與評論數排序，每類先顯示五筆。

TGOS、TDX、PLVR 真實 adapter 尚未啟用。地圖結果僅供展示，不代表正式定位、估價、投資或交通分析。
