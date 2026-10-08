import type { Metadata } from "next";
import "./globals.css";
import "leaflet/dist/leaflet.css";
import { ExperienceLocaleProvider } from "@/components/experience-locale-provider";
import { ClientErrorMonitor } from "@/components/client-error-monitor";
import { PerformanceTelemetry } from "@/components/performance-telemetry";
import { CommercialGlobalHeader } from "@/components/commercial-global-header";

export const metadata: Metadata = {
  title: "PropTech AI Copilot",
  description: "整合市場、區位、風險與資金證據的不動產評估工作區",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-Hant">
      <body><ExperienceLocaleProvider><ClientErrorMonitor /><PerformanceTelemetry /><CommercialGlobalHeader />{children}</ExperienceLocaleProvider></body>
    </html>
  );
}
