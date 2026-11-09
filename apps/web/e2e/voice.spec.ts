import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

// Chromium has real speech recognition, but it needs a microphone and Google's service, so
// every test drives a stand-in that the page cannot tell apart.
type Fake = {
  lang: string;
  started: boolean;
  onresult: ((e: unknown) => void) | null;
  onerror: ((e: unknown) => void) | null;
  onend: (() => void) | null;
};
declare global {
  interface Window {
    __speech: { last: Fake | null };
  }
}

async function withFakeSpeech(page: Page) {
  await page.addInitScript(() => {
    const state: { last: Fake | null } = { last: null };
    window.__speech = state;
    class FakeRecognition {
      lang = "";
      started = false;
      onresult: ((e: unknown) => void) | null = null;
      onerror: ((e: unknown) => void) | null = null;
      onend: (() => void) | null = null;
      constructor() {
        state.last = this;
      }
      start() {
        this.started = true;
      }
      stop() {
        this.onend?.();
      }
      abort() {
        this.onend?.();
      }
    }
    Object.assign(window, { SpeechRecognition: FakeRecognition });
  });
}

/** What the speaker says, as the browser reports it. */
const hear = (page: Page, ...parts: string[]) =>
  page.evaluate((spoken) => {
    const results = spoken.map((transcript) => ({
      0: { transcript },
      length: 1,
      isFinal: false,
    }));
    window.__speech.last?.onresult?.({ results });
  }, parts);

const fail = (page: Page, error: string) =>
  page.evaluate((code) => {
    const rec = window.__speech.last;
    rec?.onerror?.({ error: code });
    rec?.onend?.();
  }, error);

test.describe("speaking a claim", () => {
  test("fills the box, says who hears the audio, and leaves the submitting to you", async ({
    page,
  }) => {
    await withFakeSpeech(page);
    await page.goto("/");
    const box = page.getByLabel("The claim to check");
    await box.fill("Italy:");

    await page.getByRole("button", { name: "Speak" }).click();
    await expect(page.getByRole("status")).toContainText("Listening");
    await expect(page.getByRole("status")).toContainText(
      "may send the audio to its provider",
    );

    await hear(page, "debt is 133%");
    await expect(box).toHaveValue("Italy: debt is 133%");
    await hear(page, "debt is 133%", " of GDP");
    await expect(box).toHaveValue("Italy: debt is 133% of GDP");

    await page.getByRole("button", { name: "Stop" }).click();
    await expect(page.getByRole("button", { name: "Speak" })).toBeVisible();
    await expect(page.getByRole("status")).toContainText(
      "Check that every figure was heard correctly",
    );
    // Nothing was sent: still on the home page, and the button is ready for a person to press.
    await expect(page).toHaveURL(/\/$/);
    await expect(
      page.getByRole("button", { name: "Check this claim" }),
    ).toBeEnabled();
  });

  test("listens for English, with no language menu", async ({ page }) => {
    await withFakeSpeech(page);
    await page.goto("/");
    await expect(page.getByRole("combobox")).toHaveCount(0);
    await page.getByRole("button", { name: "Speak" }).click();
    await expect
      .poll(() => page.evaluate(() => window.__speech.last?.lang))
      .toBe("en-US");
  });

  test("explains a blocked microphone, and typing still works", async ({
    page,
  }) => {
    await withFakeSpeech(page);
    await page.goto("/");
    await page.getByRole("button", { name: "Speak" }).click();
    await fail(page, "not-allowed");
    await expect(page.locator("#claim-error")).toContainText(
      "The microphone is blocked",
    );
    await expect(page.getByRole("button", { name: "Speak" })).toBeVisible();
    await page.getByLabel("The claim to check").fill("Rents rose 5%.");
    await expect(
      page.getByRole("button", { name: "Check this claim" }),
    ).toBeEnabled();
  });

  test("is not offered where the browser cannot listen", async ({ page }) => {
    await page.addInitScript(() => {
      Object.assign(window, {
        SpeechRecognition: undefined,
        webkitSpeechRecognition: undefined,
      });
    });
    await page.goto("/");
    await expect(page.getByLabel("The claim to check")).toBeVisible();
    await expect(page.getByRole("button", { name: "Speak" })).toHaveCount(0);
  });

  test("works from the keyboard", async ({ page }) => {
    await withFakeSpeech(page);
    await page.goto("/");
    await page.getByRole("button", { name: "Speak" }).focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("button", { name: "Stop" })).toBeFocused();
    await hear(page, "unemployment fell");
    await page.keyboard.press("Space");
    await expect(page.getByRole("button", { name: "Speak" })).toBeFocused();
    await expect(page.getByLabel("The claim to check")).toHaveValue(
      "unemployment fell",
    );
  });

  test("fits a 360px screen and passes the accessibility scan, listening or not", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 360, height: 740 });
    await withFakeSpeech(page);
    await page.goto("/");
    const scan = async () => {
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - window.innerWidth,
      );
      expect(overflow).toBeLessThanOrEqual(0);
      const { violations } = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag22aa"])
        .analyze();
      expect(violations).toEqual([]);
    };
    await expect(page.getByRole("button", { name: "Speak" })).toBeVisible();
    await scan();
    await page.getByRole("button", { name: "Speak" }).click();
    await expect(page.getByRole("status")).toContainText("Listening");
    await scan();
  });
});
