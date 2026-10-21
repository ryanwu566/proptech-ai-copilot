import type { CopyCatalogue } from "./copy-catalogue";

export const accountEntryCopy: CopyCatalogue<"entry" | "login" | "signup" | "working"> = {
  "zh-TW": { entry: "帳戶", login: "登入", signup: "建立帳戶", working: "處理中…" },
  en: { entry: "Account", login: "Sign in", signup: "Create account", working: "Please wait…" },
  ja: { entry: "アカウント", login: "ログイン", signup: "アカウント作成", working: "処理中…" },
  ko: { entry: "계정", login: "로그인", signup: "계정 만들기", working: "처리 중…" },
};
