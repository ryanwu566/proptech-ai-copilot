import type { ExperienceLocale } from "@/lib/experience-i18n";

export type ReadAloudState = "supported" | "unavailable" | "voice_missing" | "stopped" | "speaking" | "paused" | "error";

export type SafeSpeechSummary = Readonly<{
  visibleText: string;
  locale: ExperienceLocale;
}>;

export function createSafeSpeechSummary(lines: readonly string[], locale: ExperienceLocale): SafeSpeechSummary {
  return { visibleText: lines.map((line) => line.trim()).filter(Boolean).join(". "), locale };
}

export function browserSpeechLocale(locale: ExperienceLocale): string {
  return locale === "zh-TW" ? "zh-TW" : locale === "ja" ? "ja-JP" : locale === "ko" ? "ko-KR" : "en-US";
}

export function selectSpeechVoice(voices: readonly SpeechSynthesisVoice[], locale: ExperienceLocale): SpeechSynthesisVoice | null {
  const target = browserSpeechLocale(locale).toLowerCase();
  const base = target.split("-")[0];
  return voices.find((voice) => voice.lang.toLowerCase() === target)
    ?? voices.find((voice) => voice.lang.toLowerCase().startsWith(`${base}-`))
    ?? null;
}

export function hasSpeakableSummary(summary: SafeSpeechSummary): boolean {
  return summary.visibleText.trim().length > 0;
}
