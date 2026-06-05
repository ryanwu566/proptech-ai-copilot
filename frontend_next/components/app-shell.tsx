"use client";

import { useState } from "react";
import type { ReactNode } from "react";
import { AppPage, Sidebar } from "@/components/sidebar";
import { Topbar } from "@/components/topbar";

export function AppShell({ page, onNavigate, children }: { page: AppPage; onNavigate: (page: AppPage) => void; children: ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const navigate = (next: AppPage) => { onNavigate(next); setMenuOpen(false); };
  return <div className="min-h-screen overflow-x-hidden bg-canvas"><Sidebar page={page} onNavigate={navigate} open={menuOpen} onClose={() => setMenuOpen(false)} /><main className="min-w-0 lg:pl-48"><Topbar page={page} onMenu={() => setMenuOpen(true)} /><div className="mx-auto max-w-[1440px] min-w-0 px-4 py-5 sm:px-5 lg:px-7 lg:py-6">{children}</div></main></div>;
}
