export const HELP_CONTENT = {
  decisionReport: { title: "看屋決策報告", body: "把價格、負擔、區位與風險整理成一份可分享 HTML 報告，方便和家人、朋友或客戶討論。" },
  guidedDemo: { title: "一鍵 Demo", body: "用示範條件實際呼叫 API 跑完整流程，讓你先看懂這個網站會產生什麼結果。" },
  propertyFinder: { title: "找房雷達", body: "用預算、地點和坪數，從實價登錄中找出你比較可能買得到的區域或路段。它不是即時待售物件清單。" },
  valuation: { title: "合理價格區間", body: "根據附近可比成交估算出的參考價格，幫你判斷開價是否偏高或偏低，不代表正式鑑價。" },
  trend: { title: "趨勢情境", body: "用近期交易資料看價格變化，幫你理解這個區域是偏熱、平穩還是資料不足。" },
  loan: { title: "貸款月付", body: "用總價、頭期款、利率和年限估算每月房貸，方便先看收入是否撐得住。" },
  holdingCost: { title: "持有成本", body: "房貸之外，還要加管理費、修繕、稅費和保險，這才比較接近每月真實支出。" },
  location: { title: "區位分析", body: "用附近交通、生活機能、學校、公園與醫療設施，幫你看這個地點生活方不方便。" },
  risk: { title: "風險總評", body: "把價格、月付、持有成本、區位和資料信心整理成紅黃綠燈號，幫你決定是否值得繼續看屋。" },
  taxOracle: { title: "TaxOracle 稅務快篩", body: "補充檢查房地合一稅相關條件與文件風險，只是初步快篩，不代表正式稅務申報建議。" },
  caseSave: { title: "案件保存", body: "把目前分析進度存在瀏覽器，下次可回來繼續。資料只保存在本機 localStorage，不會上傳到資料庫。" },
  caseComparison: { title: "案件比較", body: "保存兩個以上案件後，可以比較價格、月付、區位、風險和稅務快篩，幫你排序候選物件。" },
  htmlExport: { title: "HTML 匯出", body: "下載一份可用瀏覽器開啟與分享的報告，不需要另外安裝 PDF 軟體。" },
  shareLink: { title: "分享連結", body: "分享連結只帶入查詢條件，不會包含你的收入，也不會自動執行分析。" },
  mapInsight: { title: "Map Insight", body: "搜尋地址並整理附近 POI 與生活圈資訊；資料仍需搭配實地確認。" },
  geoMap: { title: "GeoMap", body: "在地圖上查看附近設施位置與距離，方便快速理解生活圈分布。" },
  dataStatus: { title: "Data Status", body: "顯示估價資料來源、期間與覆蓋範圍，幫你判斷目前分析資料是否足夠。" },
  terrainRisk: { title: "地勢與災害風險分析", body: "這是公開圖資的初步比對，不代表建築結構鑑定、土地使用限制、地質調查或正式防災結論。實際風險仍需以現場、主管機關與專業人員判定為準。" },
} as const;

export type HelpKey = keyof typeof HELP_CONTENT;
