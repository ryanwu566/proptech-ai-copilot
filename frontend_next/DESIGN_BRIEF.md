# Frontend v3 Design Brief

## 設計方向

產品定位為「房地產案件決策工作台 / Urban Intelligence Copilot」。介面以交易案件、區域地圖、風險原因與客戶報告串起操作情境，而不是一般後台或功能展示卡片集合。

- TaxOracle 是主要任務；Dashboard 引導使用者立即選案例並分析。
- Map Insight 是主要視覺亮點；地圖佔據畫面主體。
- Market Insight、房貸風險展示、判決風險摘要與歷史案件為輔助工具。
- 中文為主要操作語言；英文只保留品牌、TaxOracle、Map Insight 等短標籤。
- 減少裝飾、卡片與工程術語，以清楚的分區、線條與狀態呈現資訊。

## 色彩系統

- Canvas：`#f7f5f0`，溫暖米灰背景。
- Surface：`#ffffff`，只用於有明確用途的 panel。
- Sidebar：`#0f172a`。
- Primary：`#0f3d5e` 深藍。
- Accent：`#0891b2` cyan，少量使用於互動與地圖。
- Text：`#172033`；Secondary：`#64748b`。
- 可行：emerald；需複核：amber；高風險：rose。

## 字級系統

- Page title：30–34px / bold。
- Hero title：36–42px / bold。
- Section title：18–22px / bold。
- Body：14px / 1.6 line-height。
- Caption / label：11–12px / semibold。
- 數值：24–44px，依層級使用。

## Spacing 規則

- 頁面最大寬度：1366px。
- 頁面左右 padding：28–36px。
- Section 間距：28–36px。
- Panel padding：16–24px。
- 緊湊表格 row：44–52px。
- 元件間距以 4px 倍數為主。

## 元件規則

- 圓角以 10–12px 為主，不使用過度膨大的圓角。
- 陰影只用淡陰影；主要靠邊框與背景區分層級。
- Card 僅用於操作 panel、結果 panel、明確摘要。
- Badge 必須使用自然中文狀態。
- Empty / Error / Loading 使用同一視覺與語氣。
- 表格使用緊湊欄距、淡色 header 與清楚 row divider。

## Dashboard 資訊架構

1. Split decision workspace：案件決策文案、主要 CTA、迷你地圖與案件預覽。
2. 三個可選案件：低風險換屋案、中風險持分案、高風險非自住案。
3. 情境化分析流程：選案、稅務快篩、原因追蹤、報告輸出。
4. 不同視覺權重的補強入口：稅務、地圖、行情、風險。

## TaxOracle 頁面資訊架構

1. Page header 與四步流程。
2. 雙欄分析工作台：
   - 左：分段案例選擇、條件摘要、主要快篩動作。
   - 右：Decision card、風險環、關鍵原因與報告下載。
3. Tabs：結果原因、Rule Trace、補件清單、五年列管、AI 說明。
4. 固定免責聲明。

## Map Insight 頁面資訊架構

1. 大地圖直接成為頁面主畫布。
2. 搜尋列浮在地圖左上方。
3. 半透明 insight panel 浮在右側：生活機能、區域摘要、POI filters、免責。
4. 地圖下方使用橫向地點節點清單，不使用表格。
