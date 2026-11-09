import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { DONE_ID } from "./ids";

/** Opens every folded section, once the page has finished loading so React has taken it over. */
async function openEverything(page: Page) {
  await page.waitForLoadState("networkidle");
  await page.evaluate(() =>
    document.querySelectorAll("details").forEach((d) => (d.open = true)),
  );
}

test.describe("the methodology page", () => {
  test("is reached from the header, the footer and the home page", async ({
    page,
  }) => {
    await page.goto("/");
    await page
      .getByRole("navigation", { name: "Main" })
      .getByRole("link", { name: "Methodology" })
      .click();
    await expect(page).toHaveURL(/\/methodology$/);

    await page.goto("/");
    await page.getByRole("link", { name: "Read the full method" }).click();
    await expect(page).toHaveURL(/\/methodology$/);

    await page.goto("/");
    await page
      .getByRole("contentinfo")
      .getByRole("link", { name: "Methodology" })
      .click();
    await expect(page).toHaveURL(/\/methodology$/);
  });

  test("is reached from a receipt", async ({ page }) => {
    await page.goto(`/check/${DONE_ID}`);
    await page
      .getByRole("link", { name: "How HoldsUp judges a claim" })
      .first()
      .click();
    await expect(page).toHaveURL(/\/methodology$/);
    await expect(
      page.getByRole("heading", {
        level: 1,
        name: "How HoldsUp judges a claim",
      }),
    ).toBeVisible();
  });

  test("keeps the working folded, and a link to it opens it", async ({
    page,
  }) => {
    await page.goto("/methodology");
    // Folded: the figures are on the page but not shown.
    await expect(page.getByText("(version 2)")).toBeHidden();
    await page
      .getByRole("navigation", { name: "On this page" })
      .getByRole("link", { name: "What counts as a match" })
      .click();
    await expect(page).toHaveURL(/#match$/);
    await expect(page.getByText("(version 2)")).toBeVisible();
    const rank = page
      .getByText("A position", { exact: true })
      .locator("xpath=ancestor::div[1]");
    await expect(rank).toContainText(
      "No gap: the position has to be exactly right.",
    );

    await page
      .getByRole("navigation", { name: "On this page" })
      .getByRole("link", { name: "Known limitations" })
      .click();
    await expect(page).toHaveURL(/#limits$/);
    await expect(
      page.getByRole("heading", { level: 2, name: "Known limitations" }),
    ).toBeInViewport();
  });

  test("opens a folded section straight from its address, and from the keyboard", async ({
    page,
  }) => {
    await page.goto("/methodology#steps");
    await expect(page.getByText("It looks for an earlier check")).toBeVisible();

    // The heading is the control: Enter folds it, Enter opens it again.
    const control = page
      .locator("summary")
      .filter({ has: page.getByRole("heading", { name: "The calculations" }) });
    await expect(page.getByText("Value at a date")).toBeHidden();
    await control.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByText("Value at a date")).toBeVisible();
    await page.keyboard.press("Enter");
    await expect(page.getByText("Value at a date")).toBeHidden();
  });

  test("has no accessibility violations", async ({ page }) => {
    await page.goto("/methodology");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    const { violations } = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag22aa"])
      .analyze();
    expect(violations).toEqual([]);
  });

  test("has no accessibility violations with every section open", async ({
    page,
  }) => {
    await page.goto("/methodology");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await page.emulateMedia({ reducedMotion: "reduce" });
    await openEverything(page);
    const { violations } = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag22aa"])
      .analyze();
    expect(violations).toEqual([]);
  });

  test("fits a 360px screen without sideways scrolling, folded or open", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 360, height: 800 });
    await page.goto("/methodology");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    const sideways = () =>
      page.evaluate(
        () => document.documentElement.scrollWidth > window.innerWidth,
      );
    expect(await sideways()).toBe(false);
    await openEverything(page);
    expect(await sideways()).toBe(false);
  });
});
