"use client";

import { useEffect, useRef, useState } from "react";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { isSafeVoiceAction, parseVoiceCommand, type VoiceAction, type VoiceCommandResult, type VoiceInputState } from "@/lib/voice-input";

type RecognitionEventLike = { results: { [index: number]: { [index: number]: { transcript: string } } } };
type RecognitionLike = { lang: string; continuous: boolean; interimResults: boolean; onresult: ((event: RecognitionEventLike) => void) | null; onerror: (() => void) | null; onend: (() => void) | null; start: () => void; stop: () => void; abort: () => void };
type RecognitionConstructor = new () => RecognitionLike;

function getRecognition(): RecognitionConstructor | undefined {
  if (typeof window === "undefined") return undefined;
  const candidate = window as Window & { SpeechRecognition?: RecognitionConstructor; webkitSpeechRecognition?: RecognitionConstructor };
  return candidate.SpeechRecognition ?? candidate.webkitSpeechRecognition;
}

export function VoiceInputControls({ onAction }: { onAction?: (action: VoiceAction) => void }) {
  const { locale, t } = useExperienceLocale();
  const [state, setState] = useState<VoiceInputState>("idle");
  const [command, setCommand] = useState<VoiceCommandResult>();
  const recognitionRef = useRef<RecognitionLike | undefined>(undefined);
  const supported = Boolean(typeof window !== "undefined" && getRecognition());

  useEffect(() => () => { recognitionRef.current?.abort(); recognitionRef.current = undefined; }, []);

  function start() {
    const Constructor = getRecognition();
    if (!Constructor) { setState("unavailable"); return; }
    const recognition = new Constructor();
    recognition.lang = locale === "zh-TW" ? "zh-TW" : locale;
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.onresult = (event) => {
      const transcript = event.results[0]?.[0]?.transcript ?? "";
      const parsed = parseVoiceCommand(transcript, locale);
      setCommand(parsed);
      setState(parsed.kind === "blocked" ? "stopped" : parsed.kind === "no_match" ? "no_match" : "confirmation_required");
    };
    recognition.onerror = () => setState("error");
    recognition.onend = () => setState((current) => current === "listening" ? "stopped" : current);
    recognitionRef.current = recognition;
    setCommand(undefined);
    setState("requesting");
    try { recognition.start(); setState("listening"); } catch { setState("error"); }
  }

  function stop() { recognitionRef.current?.stop(); recognitionRef.current = undefined; setState("stopped"); }
  function cancel() { recognitionRef.current?.abort(); recognitionRef.current = undefined; setCommand(undefined); setState("cancelled"); }
  function reject() { setCommand(undefined); setState("cancelled"); }
  function confirm() {
    if (!isSafeVoiceAction(command?.action)) return;
    setState("applying");
    onAction?.(command.action);
    setCommand(undefined);
    setState("stopped");
  }

  const status = state === "listening" ? t("voice.inputListening") : state === "unavailable" ? t("voice.inputUnsupported") : state === "no_match" ? t("voice.inputNoMatch") : command?.kind === "blocked" ? t("voice.inputBlocked") : state === "confirmation_required" ? t("voice.inputConfirmation") : "";
  return <section aria-label={t("voice.inputLabel")} data-voice-input-state={state} className="flex min-w-0 flex-wrap items-center gap-1.5">
    {!supported && state === "idle" ? <span className="text-[10px] text-slate-500">{t("voice.inputUnsupported")}</span> : <>
      {state === "listening" ? <button type="button" onClick={stop} className="rounded-md border border-rose-300 bg-white px-2 py-1.5 text-[10px] font-bold text-rose-800">{t("voice.inputStop")}</button> : <button type="button" onClick={start} disabled={state === "requesting" || state === "applying"} className="rounded-md border border-violet-200 bg-violet-50 px-2 py-1.5 text-[10px] font-bold text-violet-900 disabled:opacity-50">{t("voice.inputStart")}</button>}
      {command ? <div className="basis-full rounded-md border border-violet-200 bg-violet-50 p-2 text-[10px] text-violet-950" role="status"><p>{t("voice.inputTranscript")}: {command.transcript}</p>{command.action ? <p className="mt-1">{t("voice.inputInterpretation")}: {command.action.type}</p> : null}{command.kind === "confirmation_required" ? <div className="mt-2 flex gap-1.5"><button type="button" onClick={confirm} className="rounded border border-violet-300 bg-white px-2 py-1 font-bold">{t("voice.inputConfirm")}</button><button type="button" onClick={reject} className="rounded border border-stone-300 bg-white px-2 py-1 font-bold">{t("voice.inputReject")}</button></div> : null}</div> : null}
      {(state === "listening" || command) ? <button type="button" onClick={cancel} className="rounded-md border border-stone-200 bg-white px-2 py-1.5 text-[10px] font-bold">{t("voice.inputCancel")}</button> : null}
      {status ? <span role="status" aria-live="polite" className="sr-only">{status}</span> : null}
    </>}
  </section>;
}
