"use client";

import { useEffect, useRef, useState } from "react";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { commandPaletteCopy } from "@/lib/command-palette-copy";
import { filterCaseCommands, type CaseCommand } from "@/lib/command-palette";
import styles from "./command-palette.module.css";

export function CommandPaletteDialog({ commands, onClose, onSelect, opener }: {
  commands: CaseCommand[]; onClose: () => void; onSelect: (command: CaseCommand) => void; opener: HTMLElement | null;
}) {
  const { copyFrom } = useExperienceLocale();
  const copy = (key: keyof typeof commandPaletteCopy.en, values?: Record<string, string | number>) => copyFrom(commandPaletteCopy, key, values);
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState("");
  const dialog = useRef<HTMLDialogElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  const filtered = filterCaseCommands(commands, query);
  const active = filtered.find((c) => c.id === selectedId) ?? filtered[0];

  useEffect(() => {
    const element = dialog.current;
    const previous = opener;
    const overflow = document.body.style.overflow;
    element?.showModal();
    document.body.style.overflow = "hidden";
    input.current?.focus({ preventScroll: true });
    return () => {
      element?.close();
      document.body.style.overflow = overflow;
      if (previous?.isConnected) previous.focus({ preventScroll: true });
    };
  }, [opener]);
  useEffect(() => {
    if (active) document.getElementById(`case-command-${active.id}`)?.scrollIntoView({ block: "nearest" });
  }, [active?.id]);

  function move(direction: number) {
    if (!filtered.length) return;
    const index = filtered.findIndex((c) => c.id === active?.id);
    setSelectedId(filtered[(index + direction + filtered.length) % filtered.length].id);
  }
  return <dialog ref={dialog} className={styles.dialog} data-testid="command-palette"
    aria-modal="true" aria-labelledby="case-commands-title"
    onCancel={(event) => { event.preventDefault(); onClose(); }}
    onClick={(event) => {
      if (event.target !== event.currentTarget) return;
      const rect = event.currentTarget.getBoundingClientRect();
      if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) onClose();
    }}
    onKeyDown={(event) => {
      if (event.key === "Tab") {
        if (event.shiftKey && document.activeElement === input.current) { event.preventDefault(); closeButton.current?.focus(); }
        else if (!event.shiftKey && document.activeElement === closeButton.current) { event.preventDefault(); input.current?.focus(); }
      }
    }}>
    <div className={styles.heading}><h2 id="case-commands-title">{copy("title")}</h2><kbd>Esc</kbd></div>
    <div className={styles.search}>
      <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 5 5" /></svg>
      <input ref={input} type="text" role="combobox" aria-label={copy("search")} placeholder={copy("search")} autoComplete="off" spellCheck={false}
        aria-expanded="true" aria-controls="case-commands-list" aria-autocomplete="list" aria-activedescendant={active ? `case-command-${active.id}` : undefined}
        value={query} onChange={(event) => { setQuery(event.target.value); setSelectedId(""); }}
        onKeyDown={(event) => {
          if (event.nativeEvent.isComposing) return;
          if (event.key === "ArrowDown" || event.key === "ArrowUp") { event.preventDefault(); move(event.key === "ArrowDown" ? 1 : -1); }
          if (event.key === "Enter") { event.preventDefault(); if (active) onSelect(active); }
        }} />
      <button ref={closeButton} type="button" data-testid="command-palette-close" className={styles.close} aria-label={copy("close")} onClick={onClose}>×</button>
    </div>
    <p className={styles.srOnly} role="status" aria-live="polite" aria-atomic="true" data-testid="command-results-status">{copy("results", { count: filtered.length })}</p>
    <ul id="case-commands-list" role="listbox" aria-label={copy("title")} className={styles.list}>
      {filtered.map((command) => <li key={command.id} id={`case-command-${command.id}`} data-command-id={command.id}
        role="option" aria-selected={active?.id === command.id} className={styles.option}
        onMouseDown={(event) => event.preventDefault()} onMouseMove={() => setSelectedId(command.id)} onClick={() => onSelect(command)}>
        <span className={styles.commandText}><span className={styles.commandTitle}>{command.title}</span>{command.context && <span className={styles.context}>{command.context}</span>}</span>
        {command.current && <span className={styles.current}>{copy("current")}</span>}
        {active?.id === command.id && <kbd aria-hidden="true">↵</kbd>}
      </li>)}
    </ul>
    {!filtered.length && <p className={styles.empty}>{copy("empty")}</p>}
    <footer className={styles.footer}><span><kbd>↑</kbd><kbd>↓</kbd> {copy("navigate")}</span><span><kbd>↵</kbd> {copy("select")}</span><span><kbd>Esc</kbd> {copy("dismiss")}</span></footer>
  </dialog>;
}
