"use client";

import { useEffect, useRef, useState } from "react";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { browserSpeechLocale, selectSpeechVoice } from "@/lib/safe-speech";

const COPY = {
  "zh-TW": { on: "開啟輔助朗讀", off: "關閉輔助朗讀", label: "輔助朗讀", unavailable: "瀏覽器不支援輔助朗讀", pause: "暫停", resume: "繼續", stop: "停止", repeat: "重讀" },
  en: { on: "Turn on assistive narration", off: "Turn off assistive narration", label: "Assistive narration", unavailable: "Assistive narration is unavailable", pause: "Pause", resume: "Resume", stop: "Stop", repeat: "Repeat" },
  ja: { on: "補助読み上げをオン", off: "補助読み上げをオフ", label: "補助読み上げ", unavailable: "補助読み上げは利用できません", pause: "一時停止", resume: "再開", stop: "停止", repeat: "もう一度" },
  ko: { on: "보조 읽기 켜기", off: "보조 읽기 끄기", label: "보조 읽기", unavailable: "보조 읽기를 사용할 수 없습니다", pause: "일시정지", resume: "재개", stop: "중지", repeat: "다시 읽기" },
} as const;

function readableTarget(target: EventTarget | null): HTMLElement | null {
  return target instanceof HTMLElement ? target.closest<HTMLElement>("button,a,input,select,textarea,[tabindex],summary,[role='alert'],[data-assistive-panel]") : null;
}

export function AssistiveNarrationControls() {
  const { locale } = useExperienceLocale();
  const copy = COPY[locale];
  const [enabled, setEnabled] = useState(false);
  const [supported, setSupported] = useState(true);
  const [speaking, setSpeaking] = useState(false);
  const [paused, setPaused] = useState(false);
  const voicesRef = useRef<SpeechSynthesisVoice[]>([]);
  const lastElementRef = useRef<HTMLElement | null>(null);
  const lastSpokenAtRef = useRef(0);

  useEffect(() => {
    if (typeof window === "undefined" || !window.speechSynthesis || typeof window.SpeechSynthesisUtterance === "undefined") {
      setSupported(false);
      return;
    }
    const synthesis = window.speechSynthesis;
    const updateVoices = () => { voicesRef.current = synthesis.getVoices(); };
    updateVoices();
    synthesis.addEventListener("voiceschanged", updateVoices);
    return () => { synthesis.removeEventListener("voiceschanged", updateVoices); synthesis.cancel(); };
  }, []);

  useEffect(() => {
    if (!enabled || !supported) return;
    const speakTarget = (target: EventTarget | null) => {
      const element = readableTarget(target);
      if (!element) return;
      const now = Date.now();
      if (element === lastElementRef.current && now - lastSpokenAtRef.current < 250) return;
      const label = element.dataset.assistiveLabel || element.getAttribute("aria-label") || (element instanceof HTMLSelectElement ? element.selectedOptions[0]?.textContent : element.textContent);
      const text = label?.replace(/\s+/gu, " ").trim();
      if (!text) return;
      lastElementRef.current = element;
      lastSpokenAtRef.current = now;
      const synthesis = window.speechSynthesis;
      synthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = browserSpeechLocale(locale);
      const voice = selectSpeechVoice(voicesRef.current, locale);
      if (voice) utterance.voice = voice;
      utterance.onstart = () => { setSpeaking(true); setPaused(false); };
      utterance.onpause = () => setPaused(true);
      utterance.onresume = () => setPaused(false);
      utterance.onend = () => { setSpeaking(false); setPaused(false); };
      utterance.onerror = () => { setSpeaking(false); setPaused(false); };
      synthesis.speak(utterance);
    };
    const onFocus = (event: FocusEvent) => speakTarget(event.target);
    const onClick = (event: MouseEvent) => speakTarget(event.target);
    const onChange = (event: Event) => speakTarget(event.target);
    document.addEventListener("focusin", onFocus);
    document.addEventListener("click", onClick);
    document.addEventListener("change", onChange);
    return () => { document.removeEventListener("focusin", onFocus); document.removeEventListener("click", onClick); document.removeEventListener("change", onChange); window.speechSynthesis?.cancel(); };
  }, [enabled, locale, supported]);

  if (!supported) return <span role="status" className="text-[10px] text-slate-500">{copy.unavailable}</span>;
  const toggle = () => { if (enabled) window.speechSynthesis.cancel(); setEnabled((value) => !value); setSpeaking(false); setPaused(false); };
  return <div className="flex flex-wrap items-center gap-1" data-assistive-narration={enabled ? "on" : "off"}>
    <button type="button" onClick={toggle} aria-pressed={enabled} aria-label={enabled ? copy.off : copy.on} className="rounded-md border border-violet-200 bg-violet-50 px-2 py-1.5 text-[10px] font-bold text-violet-900 focus:outline-none focus:ring-2 focus:ring-violet-500">{copy.label}</button>
    {enabled && speaking && <><button type="button" onClick={() => { if (paused) { window.speechSynthesis.resume(); } else { window.speechSynthesis.pause(); } }} aria-label={paused ? copy.resume : copy.pause} className="rounded-md border border-stone-300 bg-white px-1.5 py-1.5 text-[10px]">{paused ? copy.resume : copy.pause}</button><button type="button" onClick={() => { window.speechSynthesis.cancel(); setSpeaking(false); }} aria-label={copy.stop} className="rounded-md border border-rose-200 bg-white px-1.5 py-1.5 text-[10px] text-rose-800">{copy.stop}</button><button type="button" onClick={() => { window.speechSynthesis.cancel(); setSpeaking(false); document.querySelector<HTMLElement>("[data-page-heading]")?.focus(); }} aria-label={copy.repeat} className="rounded-md border border-stone-300 bg-white px-1.5 py-1.5 text-[10px]">{copy.repeat}</button></>}
  </div>;
}
