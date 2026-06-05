import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PropTech AI Copilot",
  description: "台灣房仲 AI 產品化展示版本",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-Hant">
      <body>{children}</body>
    </html>
  );
}
