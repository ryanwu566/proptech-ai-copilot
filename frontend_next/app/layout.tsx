import type { Metadata } from "next";
import "./globals.css";
import "leaflet/dist/leaflet.css";
import { ExperienceLocaleProvider } from "@/components/experience-locale-provider";

export const metadata: Metadata = {
  title: "PropTech AI Copilot",
  description: "台灣房仲 AI 產品化展示版本",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-Hant">
      <body><ExperienceLocaleProvider>{children}</ExperienceLocaleProvider></body>
    </html>
  );
}
