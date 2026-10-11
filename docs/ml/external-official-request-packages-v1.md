# ML-0 正式資料請求草稿（未寄出、未送件）

研究範圍：臺北市、新北市之既有住宅買賣公開資料。僅研究資料來源、
歷史可得性、交易識別、版本沿革及登記標的／權利對應；不訓練模型，
不對個別房屋出具估價。以下七件各自包含完整請求要旨，送件時附共通附件。
申請人法定資料由專案負責人在機關正式表單上另行填寫，不存入程式庫。
機關仍得依法審認資格、範圍及費用；本草稿不表示已取得申請資格或授權。

## 共通附件：期間、格式、授權及去識別化邊界

資料觀察期間為民國111年7月1日至115年6月30日（2022-07-01至2026-06-30）
之交易；優先釐清112S3及115S2。請提供自各相關資料首次對外發布起至
115年10月11日（2026-10-11）之發布與異動沿革，以及此截止日之明確完整性
範圍。季度批次請涵蓋111S3、111S4、112S1至115S2每季及與之重疊之
每月1、11、21日批次／全量重製／替代版本。此清單是請求範圍，不推定
每季標籤涵蓋同季交易或每一日均有實際發布；請機關提供真正日期與版本。
如收件後才出具證明，請分列證明出具日與所證明歷史事實之日期。

優先提供UTF-8 CSV／JSON／JSONL及欄位字典、時區與時間精度說明；
歷史原始檔以原樣ZIP提供，不重新匯出覆蓋舊版。每檔請列byte size、
SHA-256（若當時僅有其他雜湊請列演算法與原值）、版本識別、產製時間、
對外發布時間、有效時間、取得路徑、資料範圍與限制。日期只有日精度時
請明示，不補寫00:00為實際發布時刻。

不請求姓名、身分證或統一編號、出生日期、電話、電子郵件、私人聯絡資料、
買賣雙方資料、含個資契約書或原申報書。請由機關先去除個資；可使用僅供
本研究對照之非個人識別代碼及物件代碼。門牌／地建號亦請以最小必要方式
提供對照；公開研究成果只發布統計及方法，不發布逐筆物件或交易資料。

請分別說明原始公開批次、函復證明、異動清單、登記摘錄及衍生對照表之
授權版本、研究／重製／保存／程式庫引用／第三方再提供／商業利用限制、
來源註記方式、保存期限、費用及撤回條件。專案目前只請求非個人之研究
使用，不因公開資料授權自動推定本次函復或登記資料可商業再利用。

## R1 內政部地政司：歷史發布及版本連續性（E1、E4）

主旨：申請112S3、115S2及雙北研究期間實價登錄批次之歷史發布、原始位元組與版本連續性證明

內政部地政司鈞鑒：

本研究已保存112S3及115S2之目前下載檔，但不能以季別檔名或舊交易日期
證明該檔於歷史時點已公開。為建立不含時間洩漏之資料來源稽核，敬請依
共通附件期間及非個人範圍，提供貴機關既有之下列資料或可公開證明：

1. release_id、original_filename、archive_url、immutable_version_id、byte_size、
   checksum_algorithm、checksum_value、original_publication_timestamp、timezone、
   time_precision、publication_manifest、manifest_checksum及產製時間。
2. 每一原始／更正／撤回／取消／替代發布之前後版本識別、發布時間、
   受影響檔案及公開範圍；完整歷史發布清單、缺漏期間及保存政策。
3. 112S3目前保存檔之SHA-256為
   `4d9fa7be16bc9aba99e79c0f86ca27b32f46755de04e98e1dd2c8d8297b466c1`、
   14,876,099 bytes；115S2為
   `6b4c148bad106a235dddf214001d605ff9ffa45ac50561f7125c6d7fa795d4da`、
   14,705,972 bytes。敬請確認這些「確切位元組」最早可證明公開之時間，
   並說明是否曾於同網址被更新；不能確認亦請明確列為無證據。

優先提供原始ZIP及CSV／JSON發布清單、雜湊與版本證明。若舊位元組不再
留存，請提供正式函復／電子簽章證明，載明可確認的版本、檔案雜湊、
歷史公開時間、證明依據、保管紀錄與限制；僅提供目前重新匯出舊交易之
檔案，尚不足證明歷史公開位元組，敬請另說明差異。請併答共通附件授權
問題及可辦理管道／費用。此致 內政部地政司。

送件管道：[資料供應系統](https://plvr.land.moi.gov.tw/Index)供查詢／轉介；
正式資訊申請採[內政部申請表](https://ws.moi.gov.tw/Download.ashx?n=55Sz6KuL6KGoLnBkZg%3D%3D&u=LzAwMS9VcGxvYWQvT2xkRmlsZS9zaXRlX25vZGVfZmlsZS81OTEyL%2BeUs%2Biri%2BihqC5wZGY%3D)
及機關公布之書面收件方式。PLVR頁公布地政司地址為臺北市中正區徐州路
五號七樓；送件前由負責人確認當前承辦及適用表單。公開下載無帳號；
特製資料申請／付費管道可能須登入及審核。系統廠商信箱不作資料權責機關。

## R2 內政部地政司：識別語意及完整交易沿革（E2、E3）

主旨：申請實價登錄「編號」「移轉編號」官方識別規則及非個人更正、取消、替代版本對照

內政部地政司鈞鑒：

為避免將研究衍生識別誤稱官方交易識別，及避免後來更正內容回流至
先前時點，敬請就共通附件期間之雙北公開買賣資料提供正式規則與既有
非個人沿革：

1. dataset_namespace、county_scope、identifier_field（編號／移轉編號）、
   identifier_definition、uniqueness_scope、serial_reuse_policy、effective_from／to、
   quarterly_vs_full_refresh_stability、同一交易重複揭露之規則。
2. 更正是否保留原key；取消是否有公開tombstone；替代是否保留／更換key；
   若更換key，請提供權威前後key對照，而非依價量或地址相似推估。
3. 逐事件之ORIGINAL／REVISION／CANCELLATION／REPLACEMENT／DUPLICATE_RELEASE、
   event_id、非個人transaction_key、source_release_id／archive_hash、
   previous_version_id、later_version_id、duplicate_of_occurrence、
   effective_timestamp、first_publication_timestamp、cancellation_status、
   replacement_relation、可公開更正原因及理由代碼。
4. 請明列每一期間／版本之完整沿革覆蓋範圍、漏列事件、保留期限及
   「未見於下一批」是否具有取消意義。請勿以無重複資料作穩定性證明。

優先CSV／JSONL事件清單、版本關係及規則文件，每檔附SHA-256、大小與
正式版本。若不能提供逐事件資料，請提供去識別化對照、正式規則及
資料不可得範圍之函復；若完整性無法證明，亦請明示。研究者可提供本地
來源檔雜湊及物理CSV列定位供機關對照，但不需要當事人資料。授權、研究
保存及再提供範圍請分別確認，依共通附件辦理。此致 內政部地政司。

送件管道同R1；地方更正程序僅為制度線索，不以當事人更正申請書冒充
公開沿革API。不要求研究者代當事人更正任何交易。

## R3 臺北市地政局／轄管地政事務所：登記單元與權利（E5）

主旨：申請雙北研究之臺北市實價登錄與非個人建物登記單元、建物部分及移轉權利對照

臺北市政府地政局鈞鑒：

本研究需辨別實價登錄建物明細是否為同一登記住宅之主建物、附屬或
共有部分；不能將一筆建物明細推定一戶，亦不能將持分比例推定住宅完整
移轉。敬請就共通附件期間之臺北市公開買賣資料，以機關去識別化摘錄
或既有正式對照，提供：公開PLVR編號與release／archive_hash／CSV列定位、
registered_building_object_id、registered_dwelling_unit_id／count、object_role、
主建物／附屬／共有部分關係、unit_to_common_interest、address_unit_link_token、
土地／建物之required_right_numerator／denominator及實際
transferred_right_numerator／denominator、registration_effective_at、historical_version、
first_available_at、mapping_basis、限制及對照完整性。請確認建號多個部分
與住宅單元數是否有別，並保留原官方語意與欄位字典。

優先UTF-8 CSV／JSON，不含所有權人姓名、身分證、電話或當事人資料；
每份摘錄及對照附SHA-256、版本與機關確認。若只能提供建物標示部／
測量成果圖，請說明可確認的物件角色及單元範圍、無法確認之移轉權利、
PLVR連結與歷史版本，以及合法申請條件／規費。不申請包含個資的完整
謄本；若必須經利害關係資格審認，請說明合法可提供非個人摘錄之替代
方式或轉介有權機關。請另答共通附件授權問題。此致 臺北市政府地政局。

管道：[地籍謄本服務](https://land.gov.taipei/Content_List.aspx?n=D37BA350BBD48584)，
由地政局正式收件轉轄管事務所；網路核發依類別有認證／費用條件。
一般謄本仍可能含個資，不直接下載為研究輸入。

## R4 新北市地政局／轄管地政事務所：登記單元與權利（E5）

主旨：申請新北市實價登錄與非個人專有、附屬、共有建物部分及完整住宅權利之歷史對照

新北市政府地政局鈞鑒：

本研究檢視實價登錄多建物部分時，需機關證明實際登記住宅單元、
專有與共有建號角色及移轉權利；不以建物筆棟數或空間鄰近推斷。
敬請就共通附件期間之新北市公開買賣資料提供PLVR release_id／archive_hash／
非個人交易key／物理列定位、building_object_token、dwelling_unit_token／count、
main／accessory／common_role、專共用圖說或登記依據之版本、unit_link、
required_right_fraction、transferred_right_fraction（分子／分母分列）、
registration_effective_at、version_valid_from／to、first_available_at、
mapping_basis及缺漏範圍。請說明多個共有建號是否同屬一戶，及分次／
持分移轉如何與公開交易對應。

優先去除所有權人與當事人資料之CSV／JSON摘錄／對照，附每檔大小、
SHA-256及機關版本。若只有標示部／專共用圖說／測量成果可提供，請就
無法證明PLVR逐筆連結、歷史單元或移轉權利部分明確註記，並提供合法
申請資格、費用及權責轉介。請併答共通附件授權、保存與再提供問題；
不請求個資完整謄本或私人契約。此致 新北市政府地政局。

管道：[新北市地政局](https://www.land.ntpc.gov.tw/)正式收件轉轄管事務所。
[專共用圖說公告](https://www.land.ntpc.gov.tw/News_Content.aspx?n=2&s=40576)
是物件角色線索；[更正程序](https://www.tamsui.land.ntpc.gov.tw/cp.aspx?n=14312)
是權責轉介線索，二者均不代表已取得公開對照服務。

## R5 國土測繪中心：非個人歷史圖資與權責確認（E5輔助）

主旨：請確認雙北歷史地籍／建物物件圖資、版本清單及非個人登記單元對照之供應權責

內政部國土測繪中心鈞鑒：

本研究需確認共通附件期間雙北地籍／建物物件相關圖資之歷史版本，
及是否存在合法非個人物件對照；不將地圖定位當作登記權利證明。
敬請提供既有產品之product_id、layer_id、object_token、version_id、
survey／effective_date、first_publication_timestamp、archive_url、checksum、
license_version、歷史供應清單及限制，並確認是否管有建物主／附屬／共有
角色、registered_unit_count、PLVR_link或transferred_right_fraction。
若不管有，請明確說明並轉介權責地政／建管機關。

優先機器可讀產品與版本清單CSV／JSON、圖資採機關正式公開格式（如
GeoPackage／SHP，僅於核准需要時取得），附大小、SHA-256及版本證明。
若無法提供原圖資，請提供正式產品規格與歷史版本保管／供應說明函。
不請求所有權人、當事人或私人聯絡資訊；請依共通附件回答研究、加值、
再提供、費用及保存條件。此致 內政部國土測繪中心。

管道：[圖資e商城說明](https://www.nlsc.gov.tw/cp.aspx?n=16739)、
[介接申請說明](https://maps.nlsc.gov.tw/S09SOA/homePage.action?Language=ZH)。
說明頁列線上憑證、郵寄、傳真與臨櫃申購；本研究不自動申購或介接。

## R6 臺北市建築管理工程處：非個人使用執照單元沿革（E5輔助）

主旨：申請臺北市使用執照／竣工圖說之非個人住宅單元與建物角色歷史摘錄及地政對照權責

臺北市建築管理工程處鈞鑒：

敬請就共通附件研究期間提供既有可公開、非個人之permit_token、
permit_version、issue／effective_timestamp、dwelling_unit_count、approved_use、
main／accessory／common_part_role、分戶／樓層物件代碼、變更或撤銷／
取代版本關係、first_publication_timestamp及與登記建號／PLVR對照之
機關權責與已存在依據。許可戶數不能代替登記住宅單元或實際移轉權利，
因此敬請明示兩者之可對應程度。

優先UTF-8 CSV／JSON非個人摘錄與欄位字典，附byte size、SHA-256、版本；
若只能提供存根或圖說影本，請先去除起造人／所有權人／聯絡資料，
提供明確限制及正式核發版本／時間證明；如對照不存在請以函復說明。
請依共通附件說明期間、申請資格、費用及授權／研究保存／再利用條件。
此致 臺北市建築管理工程處。

管道：[建管小百科](https://cmo.gov.taipei/News_toggle.aspx?PageSize=20&n=961284F845E9477B&page=5&sms=87415A8B9CE81B16)
之執照檔案圖說申請說明；由機關正式收件轉資料保管單位。確切歷史
非個人摘錄之承辦／登入／資格仍待確認，不推定可批次公開下載。

## R7 新北市工務局：非個人使用執照單元沿革（E5輔助）

主旨：請提供新北市使用執照住宅單元、建物部分及歷史替代／撤銷關係之非個人摘錄或權責轉介

新北市政府工務局鈞鑒：

敬請就共通附件期間提供可合法公開之occupancy_permit_token、version_id、
issue／effective_timestamp、registered_or_permitted_unit_count（請區別）、
approved_use、main／accessory／common_part_role、unit_link、地政建號對照
是否存在、PLVR連結是否存在、變更／撤銷／替代版本、發布時間及限制。
研究不以核發使照推定取得所有權或移轉完整住宅權利。

優先提供去識別化UTF-8 CSV／JSON摘錄，附欄位字典、大小、SHA-256、
版本及每一時間欄位意義。若僅能提供存根／竣工圖影本，請先去除申請人、
起造人、所有權人、電話及其他個資，並提供版本確認與無法對照部分之
正式函復。若非貴局保管資料，請轉介權責機關；依共通附件確認資格、
規費、研究保存、授權及再提供限制。此致 新北市政府工務局。

管道：[工務局施工科使照股公開資訊](https://service.ntpc.gov.tw/eservice/CaseData.action?itemId=106036)
供權責轉介。該頁為「核發」使用執照，非本次歷史摘錄申請表；請機關
確認合適書面／線上申請管道後，由負責人辦理。不誤用核發申請流程。
