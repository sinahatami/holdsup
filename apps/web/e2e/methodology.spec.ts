import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { DONE_ID } from "./ids";

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

  test("prints the allowed gaps the checks use, and jumps to a section", async ({
    page,
  }) => {
    await page.goto("/methodology");
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

  test("has no accessibility violations", async ({ page }) => {
    await page.goto("/methodology");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    const { violations } = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag22aa"])
      .analyze();
    expect(violations).toEqual([]);
  });

  test("fits a 360px screen without sideways scrolling", async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 800 });
    await page.goto("/methodology");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth,
    );
    expect(overflow).toBe(false);
  });
});
