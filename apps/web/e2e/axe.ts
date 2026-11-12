import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";

/**
 * Scans the page with axe against WCAG 2.2 AA and returns what it finds.
 *
 * Motion is switched off first. Cards rise into place when a page loads and sections
 * fade in as they scroll into view, so a scan that lands mid-animation reads text as
 * lighter than it ends up and reports contrast failures that no reader sees. Reduced
 * motion turns those animations off in globals.css, so the scan sees the final colours.
 */
export async function axeViolations(page: Page) {
  await page.emulateMedia({ reducedMotion: "reduce" });
  const { violations } = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag22aa"])
    .analyze();
  return violations;
}
