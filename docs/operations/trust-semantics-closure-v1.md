# Trust Semantics Closure v1 稽核與修補紀錄

工作分支：`feat/trust-semantics-closure-v1`。僅修改 `C:/Projects/proptech-trust-semantics-v1`。
初次檢查日期：2026-10-23（Asia/Taipei）。初次稽核未 push、merge 或 deploy；#225 合併後，使用者另行授權本分支整合 main、單一提交、推送與開 PR，整合驗證見第 8 節。未修改其他 worktree。

## 1. 已驗證缺陷

先檢查遠端最新 main、兩支 PR 的說明與完整 patch，才開始修改；初次稽核結束前再次 fetch main、確認 PR HEAD 與完整變更檔案清單。以下保留初次檢查快照，整合後版本見第 8 節：

| 對象 | 檢查版本 | 狀態 |
| --- | --- | --- |
| main | `c377ee94955429ab3d4804ffd8d8a6fae8c99a52` | 包含 #222 Report 日期修正及 #223 Demo Cases |
| [PR #224](https://github.com/ryanwu566/proptech-ai-copilot/pull/224) | `e6c3a707714eae021a15436039c598ea9bde17e1` | 草稿；共享重型驗證時段尚待交接 |
| [PR #225](https://github.com/ryanwu566/proptech-ai-copilot/pull/225) | `e0f97abe2103ff8792ea2ecdfa23809dc1819a48` | 開啟中；行政區定位／Market 恢復 |

以下以真實模型、保存還原、比較投影或 React 靜態呈現重現：

- 來源無法取得卻帶有 `matched=true` 時，結果文字仍聲稱位置符合來源；未涵蓋的正向旗標還會進入重要命中摘要。
- 查詢不完整、覆蓋未知或缺少覆蓋資訊的陰性結果，被直接歸為 `no_match`；缺少 hazard／terrain 覆蓋資訊時還會推定為已涵蓋。
- 舊保存摘要的未命中狀態可壓過未涵蓋資訊；已取得地形參考資料還可能被還原成災害命中。
- 淹水命中摘要省略來源降雨情境與模擬深度；液化命中未交代區域性初級評估限制，部分查詢失敗時的摘要也未保留不完整語義。
- Compare 將受限結果的 `matched=false` 計為未命中，而非未知。
- 有收入但沒有可用負擔比例時，模型及 Overview 理由仍聲稱未提供月收入。Money 的四語系未評估文案也做了相同假設。
- 住宅總成本負擔比例可能搭配房貸情境的另一份收入，造成 Compare／Report／Copilot 共用投影互相矛盾。
- 保存快照可標記「已評估」卻缺少比例或對應收入；未評估狀態也可帶著比例。
- Risk 表格重複顯示原始狀態碼；Risk 摘要、Copilot 案件與來源時間直接顯示 ISO 字串，Copilot 案件區直接顯示內部案件 ID。

## 2. 本次修補

- 讓無法取得、不支援與未涵蓋優先於矛盾的命中旗標；保留真正的部分正向訊號及其不完整限制。
- 完整陰性結果須有明確未命中判讀與已涵蓋範圍，才能進入未命中摘要。覆蓋缺失維持未知；保存、重開亦保留此限制。
- 淹水文字保留來源提供的情境／模擬深度，說明不代表實際淹水或必然受損；液化保留官方分類並說明區域性初級評估限制。未提供的欄位不補造。
- Compare 依明確 `no_match` 狀態計數，不從單一陰性旗標推論。
- 區分收入缺失與比例缺失；Overview 使用模型提供的原因，Money 改用收入或比例不足的保守文案。
- 共用投影依負擔比例的 `loan_payment`／`total_housing_cost` 基準選擇對應收入。
- 對語義矛盾但結構有效的保存負擔評估，只在讀取投影降為未評估，清除可採用比例／基準；保留房貸、其他證據、案件可見性與原始儲存資料。必要時將分析完整度降為部分。結構損壞仍沿用既有 fail-closed 驗證。
- Risk 狀態欄沿用既有四語系標籤；安全原則與鮮度文字移除原始大寫碼。Copilot 不再顯示內部案件 ID，日期沿用既有驗證與語系格式。引用 ID、DOM 引用關聯及原始時間資料不變。

唯讀獨立審查曾指出「拒絕整份矛盾財務快照會連帶隱藏案件」與「地形仍預設已涵蓋」；兩項均新增反例、確認失敗後修正。案件診斷回歸驗證保留有效房貸與其他證據。

## 3. 變更檔案

正式程式 11 個：

- `frontend_next/components/workspace/copilot/copilot-conversation.tsx`
- `frontend_next/components/workspace/risk/risk-environment-view.tsx`
- `frontend_next/lib/workspace/case-evidence.ts`
- `frontend_next/lib/workspace/compare-difference-brief.ts`
- `frontend_next/lib/workspace/copilot-copy.ts`
- `frontend_next/lib/workspace/finance-model.ts`
- `frontend_next/lib/workspace/finance-persistence.ts`
- `frontend_next/lib/workspace/money-copy.ts`
- `frontend_next/lib/workspace/overview-model.ts`
- `frontend_next/lib/workspace/risk-buyer-copy.ts`
- `frontend_next/lib/workspace/risk-evidence-model.ts`

測試 11 個：

- `frontend_next/lib/workspace/case-evidence.test.ts`
- `frontend_next/lib/workspace/compare-difference-brief.test.ts`
- `frontend_next/lib/workspace/finance-model.test.ts`
- `frontend_next/lib/workspace/finance-persistence.test.ts`
- `frontend_next/lib/workspace/overview-model.test.ts`
- `frontend_next/lib/workspace/risk-buyer-copy.test.ts`
- `frontend_next/lib/workspace/risk-evidence-model.test.ts`
- `frontend_next/lib/workspace/saved-case-diagnostics.test.ts`
- `frontend_next/scripts/trust-semantics-presentation.test.cjs`（新增）
- `frontend_next/e2e/commercial-overview-save.spec.ts`
- `frontend_next/e2e/commercial-risk-environment.spec.ts`

文件 2 個：本紀錄，以及 `docs/superpowers/plans/2026-10-23-trust-semantics-closure.md`。

## 4. 驗證

- 修改前先跑相關 native 測試：82 通過；新增缺陷反例後確認失敗，再修正。
- 最終相關 native TypeScript 契約：234 通過，0 失敗。涵蓋 Risk、Money、Overview、共用證據、Compare、Report core／executive、Copilot、日期、保存還原與案件診斷。
- React 靜態呈現與 Save／Reopen 契約：69 通過，0 失敗。命令：`node --test scripts/trust-semantics-presentation.test.cjs scripts/commercial-trust-flow.test.cjs scripts/case-storage-roundtrip.test.cjs`。
- Python 聚焦來源與信任邊界：62 通過，0 失敗。命令：`python -m pytest -q tests/test_wra_flood_provider.py tests/test_terrain_risk_providers.py tests/test_terrain_risk_transparency.py tests/test_price_affordability_trust_boundary.py`。
- `npm run typecheck`：通過。變更檔案 ESLint：0 錯誤，2 項既有設定造成的 E2E 檔案略過警告；其餘變更檔案無警告。`git diff --check`：通過。
- 兩份相關 E2E 檔案更新顯示文字斷言；Playwright `--list` 成功列出 Chromium 23 項，這僅為測試載入檢查，未宣稱瀏覽器測試已執行。
- 遵守共享資源限制，未跑 production build、完整 Playwright、完整 Python suite 或版面／實體 PDF 驗證。
- 本機使用 Node `24.14.1`；#224 記錄的固定環境為 `24.21.0`。未更改版本設定或 lockfile。

本地完整輸出在 git 忽略的 `artifacts/trust-semantics-*-tests.log`；不將測試輸出納入變更。

## 5. 與 #224／#225 的重疊

對兩支 PR 的完整變更檔案清單比對，本次 **檔案交集為零**，沒有修改其擁有的程式或測試。

仍有語義整合重疊，已避讓：

| 擁有者／檔案 | 已確認問題 | 必要後續 |
| --- | --- | --- |
| #224：`components/workspace/overview/overview-view.tsx` | 未評估的摘要卡仍硬編為缺少月收入 | 改為不假定原因，或依可用模型原因呈現 |
| #224 新增：`lib/workspace/overview-presentation.ts` | 英／日／韓的 `finance-affordability-unassessed` 翻譯會覆寫模型原因，再次聲稱未提供收入；`unassessed` 標籤亦相同 | Owner 同步四語系原因，測試「收入存在、比例缺失」 |
| #224：`components/workspace/risk/risk-buyer-card.tsx` | main 卡片顯示原始碼；#224 只移至來源詳情，詳情仍有原始狀態、ISO 時間、主題 key／canonical 類別識別 | Owner 使用既有語系狀態及日期呈現，保留內部追溯契約 |
| #224：`components/workspace/finance/finance-workspace.tsx` | 過期／修改中情境仍可在評估區顯示先前比例，其他區塊才提示鮮度 | Owner 確認此區比例明確標示先前評估；不要呈現為本次負擔結論 |
| #225：`lib/case-storage.ts` 等 | 共享保存入口；本次只修正其呼叫的財務正規化函式 | 保留 #225 的修復鎖定、取消與 evidence 保存；整合後重跑保存契約 |

Risk 的原始來源紀錄 disclosure 仍保留收到的來源資訊，未重寫其 JSON。不能把本分支描述成已清除所有技術詳情中的原始值。

## 6. 剩餘阻擋

- 整體 Trust Semantics 完整關閉仍須 #224 owner 處理上表的呈現／翻譯重疊；本次沒有跨入其檔案。
- #224 自身仍為草稿且要求不要合併；目前版本已記錄建置與多項版面驗證通過，仍待其最終整合瀏覽器與 CI 結果。本分支的聚焦驗證不能替代其餘驗證，也未更動 #224。
- 三者整合後仍需在可用重型時段執行相關瀏覽器與報告列印驗證；23 項 E2E 目前僅確認載入成功。
- #225 所述 production backend 行政區缺失仍需要另行授權的後端發布；本次不部署，也不宣稱線上已恢復。

## 7. 精確建議合併順序

1. **#225（已完成合併）**：先落地定位行政區與保存恢復契約。
2. **`feat/trust-semantics-closure-v1` 本分支**：合併本次可獨立驗證的證據與文案修正；使用者已授權單一提交、push 與開 PR，未授權合併 PR。
3. **#224**：Owner 先吸收前兩者、完成上述重疊修正與既定驗證，再解除草稿並合併。

理由：先固定行政區與證據語義，再驗證最後的四語系呈現，避免 #224 的硬編文案重新引入缺少收入的錯誤主張。這是建議順序，本次未執行任何合併。

初次完成紀錄：安全範圍的修補與聚焦驗證完成時，24 個變更檔案保留於本地工作目錄，當時未提交或推送。完整信任語義關閉仍受第 6 節的重疊與整合驗證限制。

## 8. #225 合併後的整合驗證

使用者明確授權：保留全部現有修補、整合最新 main、執行聚焦驗證，乾淨後建立一個 Closure 提交、推送並開啟對 main 的 PR；不合併 PR、不部署、不修改 #224 或其他 worktree。

| 項目 | 結果 |
| --- | --- |
| 最新 `origin/main` | `714d082ec64f12ee31e8a33f77f63531d8b94749` |
| #225 | 已合併；merge commit 即上述 main SHA |
| #224 唯讀檢查版本 | `c3f866fbee4432ad86a572330d149b7384c7a35c`，仍為草稿 |
| main 整合方式 | 從 `c377ee9` 執行 `git merge --ff-only origin/main`，未新增 merge commit |
| 原有修補保留 | 24 個檔案先做獨立備份及 SHA-256 manifest，暫存後快轉並還原；逐檔位元組一致 |
| 行尾處理 | stash 還原會依 Git 設定轉換 3 個新檔案的行尾；確認僅行尾差異後還原原始位元組，再驗證 24 個 hash 全數一致 |
| 整合期間程式修改 | 無；僅更新本報告與既有計畫的整合紀錄 |
| 相對 main 的變更範圍 | 24 個檔案：11 程式、11 測試、2 文件 |
| #225 檔案保護 | 14 個上游變更檔案與 main 逐一相同，`git diff --quiet origin/main -- <14 files>` 通過 |
| 與 #225／最新 #224 的變更檔案交集 | 均為 0 |

整合後重新執行的聚焦驗證：

- 原報告列出的 24 份 native TypeScript 契約：**234 通過、0 失敗**。
- 原報告的 React 呈現／commercial trust flow／storage roundtrip：**75 通過、0 失敗**。原為 69，新增的 6 項來自已合併 #225 的保存、鎖定與取消契約，沒有修改這些上游測試。
- #225 定位確認、行政區修復、Location 啟動交接與 Market refresh 契約：**34 通過、0 失敗**。
- 原報告 4 份 Python 來源／信任契約，加上 `tests/test_location_market_admin_contract.py`：**68 通過、0 失敗**；1 項既有 FastAPI／Starlette TestClient 棄用警告。
- `npm run typecheck`：**通過**。
- 變更檔案 ESLint：**0 錯誤**；2 項 E2E 檔案依既有規則忽略的警告。
- 原報告 2 份 E2E 加上 #225 的 `location-market-admin.spec.ts`：Playwright `--list` **成功列出 Chromium 43 項／3 檔案**。僅確認載入，沒有將其計入通過測試數。
- `git diff --check`：**通過**。

聚焦執行的測試共 **411 項通過**。沒有執行 production build、完整 Python suite、瀏覽器 suite、外部 provider 取得或部署。工具環境仍為 Node `24.14.1`／npm `11.11.0`；未更動版本設定或 lockfile。

完整本地輸出：`artifacts/trust-integration-native-tests.log`、`trust-integration-render-storage-tests.log`、`trust-integration-admin-tests.log`、`trust-integration-python-tests.log`、`trust-integration-typecheck.log`、`trust-integration-eslint.log`、`trust-integration-e2e-list.log`（均不納入提交）。

本分支在此次聚焦整合範圍沒有已知阻擋；#224 擁有的剩餘文案／來源詳情問題仍留在第 5 節，不能將它們宣稱為已關閉。開 PR 後仍須觀察該精確提交的遠端 CI，不能將本地聚焦通過視為遠端完整 release gate 已通過。
