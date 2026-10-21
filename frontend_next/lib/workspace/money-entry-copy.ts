import type { CopyCatalogue } from "../copy-catalogue";

// Shared navigation needs only the entry title, not the full Money catalogue.
export const moneyEntryCopy: CopyCatalogue<"title"> = {
  "zh-TW": { title: "購屋資金" },
  en: { title: "Money" },
  ja: { title: "購入資金" },
  ko: { title: "매입 자금" },
};
