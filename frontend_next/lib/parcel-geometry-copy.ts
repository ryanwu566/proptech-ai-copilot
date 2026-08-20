import type { ExperienceLocale } from "@/lib/experience-i18n";

export type ParcelGeometryCopy = {
  uploadTitle: string; supported: string; choose: string; replace: string; remove: string;
  reading: string; validating: string; ready: string; userProvided: string; pointReference: string;
  officialVector: string; sectionContext: string; computedArea: string; computedAreaDisclaimer: string;
  legalDisclaimer: string; invalidFile: string; unknownCrs: string; mismatch: string; consistent: string;
  notChecked: string; reupload: string; repaired: string; landsectLimitation: string;
  markerLegend: string; uploadLegend: string; officialLegend: string; sectionLegend: string;
  radiusLegend: string; spatialAvailable: string;
};

const copy: Record<ExperienceLocale, ParcelGeometryCopy> = {
  "zh-TW": {
    uploadTitle: "上傳土地 GIS 幾何（選用）", supported: "支援 GeoJSON、KML、SHP ZIP，檔案上限 10 MB。SHP ZIP 須含 .shp、.shx、.dbf 與 .prj。",
    choose: "選擇 GIS 檔案", replace: "更換幾何", remove: "移除幾何", reading: "讀取檔案", validating: "驗證幾何並正規化 CRS", ready: "幾何已載入",
    userProvided: "使用者提供", pointReference: "點位參考", officialVector: "官方向量", sectionContext: "段籍圖背景",
    computedArea: "計算幾何面積", computedAreaDisclaimer: "此為上傳幾何的投影計算面積，不是法定登記面積。",
    legalDisclaimer: "上傳幾何由使用者提供，不代表官方地籍、法定界址、所有權或測量成果。檔案僅於本次請求處理，不會保存或傳送至第三方。",
    invalidFile: "檔案無法解析或幾何無效。", unknownCrs: "無法辨識 SHP 的 CRS；請提供有效 .prj。",
    mismatch: "地址點位可能與上傳幾何不一致，請確認檔案與物件是否相符。", consistent: "地址點位位於或接近上傳幾何。", notChecked: "尚未檢查地址與幾何的一致性。",
    reupload: "重新載入此案例時需再次上傳 GIS 檔案。", repaired: "幾何拓撲已修復，使用前請核對圖形。", landsectLimitation: "LANDSECT 僅提供官方段籍圖背景，不是宗地界線。",
    markerLegend: "分析地址點位", uploadLegend: "使用者上傳幾何", officialLegend: "官方宗地向量（未設定）", sectionLegend: "LANDSECT 段籍背景", radiusLegend: "分析半徑（非界址）", spatialAvailable: "可進行幾何空間分析",
  },
  en: {
    uploadTitle: "Upload parcel GIS geometry (optional)", supported: "GeoJSON, KML, or SHP ZIP, up to 10 MB. SHP ZIP must include .shp, .shx, .dbf, and .prj.",
    choose: "Choose GIS file", replace: "Replace geometry", remove: "Remove geometry", reading: "Reading file", validating: "Validating geometry and normalizing CRS", ready: "Geometry loaded",
    userProvided: "User provided", pointReference: "Point reference", officialVector: "Official vector", sectionContext: "Section context",
    computedArea: "Computed geometry area", computedAreaDisclaimer: "This is projected area computed from the uploaded geometry, not registered legal area.",
    legalDisclaimer: "Uploaded geometry is user-provided. It is not official cadastral, legal boundary, ownership, or survey evidence. The file is request-scoped and is not stored or sent to third parties.",
    invalidFile: "The file could not be parsed or contains invalid geometry.", unknownCrs: "The SHP CRS is unknown; include a valid .prj file.",
    mismatch: "The address marker may not match the uploaded geometry. Confirm the file belongs to this property.", consistent: "The address marker is inside or near the uploaded geometry.", notChecked: "Address-to-geometry consistency has not been checked.",
    reupload: "Re-upload the GIS file after reopening this case.", repaired: "Geometry topology was repaired; review the rendered shape before use.", landsectLimitation: "LANDSECT is official cadastral section map context, not a parcel boundary.",
    markerLegend: "Analyzed address marker", uploadLegend: "User-uploaded geometry", officialLegend: "Official parcel vector (not configured)", sectionLegend: "LANDSECT section context", radiusLegend: "Analysis radius (not a boundary)", spatialAvailable: "Geometric spatial analysis available",
  },
  ja: {
    uploadTitle: "土地 GIS ジオメトリをアップロード（任意）", supported: "GeoJSON、KML、SHP ZIP（最大 10 MB）。SHP ZIP には .shp、.shx、.dbf、.prj が必要です。",
    choose: "GIS ファイルを選択", replace: "ジオメトリを置換", remove: "ジオメトリを削除", reading: "ファイルを読み込み中", validating: "ジオメトリ検証・CRS 正規化中", ready: "ジオメトリを読み込みました",
    userProvided: "ユーザー提供", pointReference: "地点参照", officialVector: "公式ベクター", sectionContext: "地籍セクション背景", computedArea: "計算ジオメトリ面積", computedAreaDisclaimer: "アップロード形状から投影計算した面積で、法定登記面積ではありません。",
    legalDisclaimer: "アップロード形状はユーザー提供で、公式地籍、法的境界、所有権、測量成果ではありません。ファイルはリクエスト内だけで処理し、保存・第三者送信しません。",
    invalidFile: "ファイルを解析できないか、ジオメトリが無効です。", unknownCrs: "SHP の CRS を識別できません。有効な .prj を含めてください。", mismatch: "住所地点とアップロード形状が一致しない可能性があります。対象物件を確認してください。", consistent: "住所地点はアップロード形状の内部または近くです。", notChecked: "住所と形状の整合性は未確認です。",
    reupload: "ケースを再度開いた後は GIS ファイルを再アップロードしてください。", repaired: "ジオメトリのトポロジーを修復しました。利用前に形状を確認してください。", landsectLimitation: "LANDSECT は公式の地籍セクション背景であり、筆界ではありません。",
    markerLegend: "分析住所地点", uploadLegend: "ユーザーアップロード形状", officialLegend: "公式筆ベクター（未設定）", sectionLegend: "LANDSECT セクション背景", radiusLegend: "分析半径（境界ではない）", spatialAvailable: "幾何学的空間分析が可能",
  },
  ko: {
    uploadTitle: "토지 GIS 지오메트리 업로드(선택)", supported: "GeoJSON, KML, SHP ZIP(최대 10 MB). SHP ZIP에는 .shp, .shx, .dbf, .prj가 필요합니다.",
    choose: "GIS 파일 선택", replace: "지오메트리 교체", remove: "지오메트리 제거", reading: "파일 읽는 중", validating: "지오메트리 검증 및 CRS 정규화 중", ready: "지오메트리 로드됨",
    userProvided: "사용자 제공", pointReference: "점 위치 참고", officialVector: "공식 벡터", sectionContext: "지적 구획 배경", computedArea: "계산된 지오메트리 면적", computedAreaDisclaimer: "업로드 형상에서 투영 계산한 면적이며 법적 등록 면적이 아닙니다.",
    legalDisclaimer: "업로드 형상은 사용자 제공 자료이며 공식 지적, 법적 경계, 소유권 또는 측량 결과가 아닙니다. 파일은 요청 중에만 처리되고 저장하거나 제3자에게 전송하지 않습니다.",
    invalidFile: "파일을 해석할 수 없거나 지오메트리가 유효하지 않습니다.", unknownCrs: "SHP CRS를 확인할 수 없습니다. 유효한 .prj를 포함하세요.", mismatch: "주소 점과 업로드 형상이 일치하지 않을 수 있습니다. 해당 부동산의 파일인지 확인하세요.", consistent: "주소 점이 업로드 형상 내부 또는 가까이에 있습니다.", notChecked: "주소와 형상의 일치 여부를 확인하지 않았습니다.",
    reupload: "사례를 다시 열면 GIS 파일을 다시 업로드해야 합니다.", repaired: "지오메트리 위상을 복구했습니다. 사용 전에 표시된 형상을 확인하세요.", landsectLimitation: "LANDSECT는 공식 지적 구획 지도 배경이며 필지 경계가 아닙니다.",
    markerLegend: "분석 주소 점", uploadLegend: "사용자 업로드 형상", officialLegend: "공식 필지 벡터(미설정)", sectionLegend: "LANDSECT 구획 배경", radiusLegend: "분석 반경(경계 아님)", spatialAvailable: "기하학적 공간 분석 가능",
  },
};

export function getParcelGeometryCopy(locale: ExperienceLocale): ParcelGeometryCopy {
  return copy[locale] ?? copy["zh-TW"];
}
