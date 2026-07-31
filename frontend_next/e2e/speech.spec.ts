import { expect, test } from "./fixtures";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    const calls: string[] = [];
    class FakeUtterance {
      text: string;
      lang = "";
      voice: SpeechSynthesisVoice | null = null;
      onstart: (() => void) | null = null;
      onend: (() => void) | null = null;
      onpause: (() => void) | null = null;
      onresume: (() => void) | null = null;
      onerror: (() => void) | null = null;
      constructor(text: string) { this.text = text; }
    }
    const synthesis = {
      speaking: false,
      paused: false,
      getVoices: () => [{ lang: "en-US", name: "Test English", default: true }],
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      speak: (utterance: FakeUtterance) => { calls.push(utterance.text); synthesis.speaking = true; utterance.onstart?.(); },
      cancel: () => { synthesis.speaking = false; },
      pause: () => { synthesis.paused = true; },
      resume: () => { synthesis.paused = false; },
    };
    Object.defineProperty(window, "speechSynthesis", { configurable: true, value: synthesis });
    Object.defineProperty(window, "SpeechSynthesisUtterance", { configurable: true, value: FakeUtterance });
    Object.defineProperty(window, "__assistiveSpeechCalls", { configurable: true, value: calls });
  });
});

test("assistive narration is explicit opt-in and responds to focus", async ({ page }) => {
  await page.goto("/");
  const toggle = page.getByRole("button", { name: /assistive|輔助|補助|보조/i });
  await expect(toggle).toHaveAttribute("aria-pressed", "false");
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: /Map|地圖|地図|지도/i }).first().click();
  await page.locator("[data-page-heading]").focus();
  await expect.poll(() => page.evaluate(() => (window as Window & { __assistiveSpeechCalls?: string[] }).__assistiveSpeechCalls?.length ?? 0)).toBeGreaterThan(0);
});
