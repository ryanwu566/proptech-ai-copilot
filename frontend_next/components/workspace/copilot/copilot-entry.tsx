"use client";
import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { copilotEntryLabel } from "@/lib/workspace/copilot-entry-copy";
import styles from "./copilot.module.css";

const Conversation = dynamic(() => import("./copilot-conversation").then(module => module.CopilotConversation));
export function CopilotEntry() {
  const { locale } = useExperienceLocale();
  const [open, setOpen] = useState(false);
  useEffect(() => { if (new URLSearchParams(window.location.search).get("copilot") === "1") setOpen(true); }, []);
  return <section className={styles.entry} data-testid="copilot-entry">
    <button type="button" className="ds-button ds-button--secondary" aria-expanded={open} aria-controls="property-copilot" onClick={() => setOpen(!open)}>{copilotEntryLabel(locale)}</button>
    {open && <div id="property-copilot"><Conversation /></div>}
  </section>;
}
