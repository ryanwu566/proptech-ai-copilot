import type { CopyCatalogue } from "../copy-catalogue";

// Only entry-point labels belong in shared client bundles. The lab's complete
// catalogue is supplied as data by its server route after explicit navigation.
export const scenarioEntryCopy: CopyCatalogue<"nav" | "readonly"> = {
  "zh-TW": { nav: "情境實驗室", readonly: "已保存證據維持凍結" },
  en: { nav: "Scenario Lab", readonly: "Frozen saved evidence" },
  ja: { nav: "シナリオラボ", readonly: "保存エビデンスは固定" },
  ko: { nav: "시나리오 랩", readonly: "저장 근거 고정" },
};
