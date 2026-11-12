import { expect, test, type Page } from "@playwright/test";
import { axeViolations } from "./axe";

/** The checks on show: one link to a receipt for each. */
const cards = (page: Page) => page.locator('a[href^="/check/"]');

test.describe("the recent checks page", () => {
  test("lists the checks a page at a time, and adds more on request", async ({
    page,
  }) => {
    await page.goto("/recent");
    await expect(page.getByRole("status")).toHaveText(
      "Showing 12 of 14 checks",
    );
    await expect(cards(page)).toHaveCount(12);
    await page.getByRole("button", { name: "Show more checks" }).click();
    await expect(cards(page)).toHaveCount(14);
    await expect(page.getByRole("status")).toHaveText(
      "Showing 14 of 14 checks",
    );
    await expect(
      page.getByRole("button", { name: "Show more checks" }),
    ).toHaveCount(0);
  });

  test("narrows by verdict, topic and place, and says when nothing is left", async ({
    page,
  }) => {
    await page.goto("/recent");
    await page.getByRole("button", { name: /^Does not hold up/ }).click();
    // Verdicts, places and topics take turns in threes: claims 2, 5, 8, 11 and 14.
    await expect(cards(page)).toHaveCount(5);

    await page.getByRole("button", { name: /^Health/ }).click();
    await expect(cards(page)).toHaveCount(5);
    await page.getByLabel("Place").selectOption("FR");
    await expect(cards(page)).toHaveCount(5);

    await page.getByLabel("Place").selectOption("DE");
    await expect(
      page.getByText("No check matches these filters."),
    ).toBeVisible();

    await page.getByRole("button", { name: "Clear filters" }).click();
    await expect(cards(page)).toHaveCount(12);
    expect(new URL(page.url()).search).toBe("");
  });

  test("keeps the filter in the address, so a link opens the same view", async ({
    page,
  }) => {
    await page.goto("/recent");
    await page.getByRole("button", { name: /^Partly holds up/ }).click();
    await expect
      .poll(() => new URL(page.url()).search)
      .toBe("?verdict=partly_supported");

    await page.goto("/recent?verdict=partly_supported&place=DE");
    await expect(page.getByLabel("Place")).toHaveValue("DE");
    // Every third check is a partial hold, and the same ones are in Germany: 3, 6, 9 and 12.
    await expect(cards(page)).toHaveCount(4);
    await expect(
      page.getByRole("button", { name: /^Partly holds up/ }),
    ).toHaveAttribute("aria-pressed", "true");
  });

  test("is reached from the home page and the footer", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "See all recent checks" }).click();
    await expect(page).toHaveURL(/\/recent$/);
    await page
      .getByRole("contentinfo")
      .getByRole("link", { name: "Recent checks" })
      .click();
    await expect(page).toHaveURL(/\/recent$/);
  });

  test("has no accessibility violations, filtered or empty", async ({
    page,
  }) => {
    await page.goto("/recent");
    await expect(page.getByRole("status")).toBeVisible();
    const scan = () => axeViolations(page);
    expect(await scan()).toEqual([]);
    await page.getByRole("button", { name: /^Does not hold up/ }).click();
    await page.getByLabel("Place").selectOption("DE");
    await expect(
      page.getByText("No check matches these filters."),
    ).toBeVisible();
    expect(await scan()).toEqual([]);
  });

  test("fits a 360px screen without sideways scrolling", async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 800 });
    await page.goto("/recent");
    await expect(page.getByRole("status")).toBeVisible();
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth,
    );
    expect(overflow).toBe(false);
  });
});
