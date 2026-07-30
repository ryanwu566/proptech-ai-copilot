"use client";

import { useEffect, useRef, useState } from "react";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { browserSpeechLocale, hasSpeakableSummary, type ReadAloudState, type SafeSpeechSummary } from "@/lib/safe-speech";

type SpeechVoiceLike = SpeechSynthesisVoice;

export function ReadAloudControls({ summary }: { summary: SafeSpeechSummary }) {
  const { t, locale } = useExperienceLocale();
  const [state, setState] = useState<ReadAloudState>("stopped");
  const [voices, setVoices] = useState<SpeechVoiceLike[]>([]);
  const synthesisRef = useRef<SpeechSynthesis | null>(null);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  useEffect(() => {
    if (typeof window === "undefined" || !window.speechSynthesis) {
      setState("unavailable");
      return;
    }
    const synthesis = window.speechSynthesis;
    synthesisRef.current = synthesis;
    const updateVoices = () => setVoices(synthesis.getVoices());
    updateVoices();
    synthesis.addEventListener("voiceschanged", updateVoices);
    return () => {
      synthesis.removeEventListener("voiceschanged", updateVoices);
      synthesis.cancel();
      synthesisRef.current = null;
      utteranceRef.current = null;
    };
  }, []);

  useEffect(() => {
    synthesisRef.current?.cancel();
    utteranceRef.current = null;
    setState((current) => current === "unavailable" ? current : "stopped");
  }, [locale]);

  function start() {
    const synthesis = synthesisRef.current;
    if (!synthesis) { setState("unavailable"); return; }
    if (!hasSpeakableSummary(summary)) { setState("error"); return; }
    const language = browserSpeechLocale(locale);
    const voice = voices.find((candidate) => candidate.lang.toLowerCase() === language.toLowerCase() || candidate.lang.toLowerCase().startsWith(`${language.toLowerCase()}-`));
    if (!voice) { setState("voice_missing"); return; }
    synthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(summary.visibleText);
    utterance.lang = language;
    utterance.voice = voice;
    utterance.onstart = () => setState("speaking");
    utterance.onpause = () => setState("paused");
    utterance.onresume = () => setState("speaking");
    utterance.onend = () => setState("stopped");
    utterance.onerror = () => setState("error");
    utteranceRef.current = utterance;
    setState("supported");
    synthesis.speak(utterance);
  }

  useEffect(() => {
    const stopFromVoice = () => stop();
    const repeatFromVoice = () => start();
    window.addEventListener("proptech:stop-read-aloud", stopFromVoice);
    window.addEventListener("proptech:repeat-read-aloud", repeatFromVoice);
    return () => {
      window.removeEventListener("proptech:stop-read-aloud", stopFromVoice);
      window.removeEventListener("proptech:repeat-read-aloud", repeatFromVoice);
    };
  }, []);

  function pause() { synthesisRef.current?.pause(); setState("paused"); }
  function resume() { synthesisRef.current?.resume(); setState("speaking"); }
  function stop() { synthesisRef.current?.cancel(); utteranceRef.current = null; setState("stopped"); }

  const stateLabel = state === "speaking" ? t("voice.statusSpeaking") : state === "paused" ? t("voice.statusPaused") : state === "voice_missing" ? t("voice.statusMissing") : state === "unavailable" ? t("voice.statusUnavailable") : state === "error" ? t("voice.statusError") : state === "supported" ? t("voice.statusSupported") : t("voice.statusStopped");
  return <div className="flex min-w-0 flex-wrap items-center gap-1.5" data-read-aloud-state={state}>
    {state === "unavailable" ? <span className="text-[10px] text-slate-500">{stateLabel}</span> : <>
      {state === "speaking" || state === "paused" ? <>
        {state === "speaking" ? <button type="button" onClick={pause} aria-label={t("voice.pause")} className="rounded-md border border-stone-300 bg-white px-2 py-1.5 text-[10px] font-bold focus:outline-none focus:ring-2 focus:ring-cyan-500">{t("voice.pause")}</button> : <button type="button" onClick={resume} aria-label={t("voice.resume")} className="rounded-md border border-stone-300 bg-white px-2 py-1.5 text-[10px] font-bold focus:outline-none focus:ring-2 focus:ring-cyan-500">{t("voice.resume")}</button>}
        <button type="button" onClick={stop} aria-label={t("voice.stop")} className="rounded-md border border-rose-300 bg-white px-2 py-1.5 text-[10px] font-bold text-rose-800 focus:outline-none focus:ring-2 focus:ring-rose-500">{t("voice.stop")}</button>
      </> : <button type="button" onClick={start} aria-label={t("voice.readAloud")} className="rounded-md border border-cyan-200 bg-cyan-50 px-2 py-1.5 text-[10px] font-bold text-cyan-900 focus:outline-none focus:ring-2 focus:ring-cyan-500">{t("voice.readAloud")}</button>}
      <span role="status" aria-live="polite" className="sr-only">{stateLabel}</span>
    </>}
  </div>;
}
