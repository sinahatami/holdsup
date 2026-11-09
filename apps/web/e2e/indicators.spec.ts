import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

/** The statistics on show, by name; assertions on it wait until the list settles. */
const names = (page: import("@playwright/test").Page) =>
  page.getByRole("heading", { level: 3 });

test.describe("the catalog page", () => {
  test("lists every statistic with its source and the places it covers", async ({
    page,
  }) => {
    await page.goto("/indicators");
    await expect(page.getByRole("status")).toHaveText("3 statistics");
    const card = page.getByRole("listitem").filter({ hasText: "Rent prices" });
    await expect(card).toContainText("prc_hicp_aind");
    await expect(card).toContainText("2005 to 2022");
    await expect(
      page.getByRole("listitem").filter({ hasText: "Unemployment rate" }),
    ).toContainText("Every country and the world as a whole");
  });

  test("narrows by words, topic, place and years together, and says when nothing is left", async ({
    page,
  }) => {
    await page.goto("/indicators");
    await page.getByLabel("Search").fill("rate");
    await expect(page.getByRole("status")).toHaveText("2 of 3 statistics");

    await page.getByLabel("Place").selectOption("NO");
    await expect(names(page)).toHaveCount(2);

    await page.getByRole("button", { name: /^Poverty/ }).click();
    await expect(names(page)).toHaveText([
      "At-risk-of-poverty rate (Eurostat)",
    ]);

    await page.getByLabel("From year").fill("2030");
    await expect(page.getByRole("status")).toHaveText("1 of 3 statistics");
    await page.getByLabel("Search").fill("zebra");
    await expect(
      page.getByText("No statistic matches these filters."),
    ).toBeVisible();

    await page.getByRole("button", { name: "Clear filters" }).click();
    await expect(page.getByRole("status")).toHaveText("3 statistics");
    expect(new URL(page.url()).search).toBe("");
  });

  test("keeps the filter in the address, so a link opens the same view", async ({
    page,
  }) => {
    await page.goto("/indicators");
    await page.getByLabel("Search").fill("rent");
    await expect.poll(() => new URL(page.url()).search).toBe("?q=rent");

    await page.goto("/indicators?theme=work&place=BR");
    await expect(page.getByLabel("Place")).toHaveValue("BR");
    await expect(names(page)).toHaveText(["Unemployment rate (World Bank)"]);
    await expect(
      page.getByRole("button", { name: /^Work and pay/ }),
    ).toHaveAttribute("aria-pressed", "true");
  });

  test("works with the keyboard alone", async ({ page }) => {
    await page.goto("/indicators");
    await page.getByLabel("Search").focus();
    await page.keyboard.type("poverty");
    await expect(page.getByRole("status")).toHaveText("1 of 3 statistics");
    await page.keyboard.press("Tab");
    await expect(
      page.getByRole("button", { name: /^All topics/ }),
    ).toBeFocused();
  });

  test("has no accessibility violations, filtered or empty", async ({
    page,
  }) => {
    await page.goto("/indicators");
    const scan = () =>
      new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag22aa"])
        .analyze();
    expect((await scan()).violations).toEqual([]);
    await page.getByLabel("From year").fill("2020");
    await page.getByLabel("To year").fill("2010");
    await expect(
      page.getByText("The first year comes after the last year."),
    ).toBeVisible();
    expect((await scan()).violations).toEqual([]);
    await page.getByLabel("Search").fill("zebra");
    expect((await scan()).violations).toEqual([]);
  });

  test("fits a 360px screen without sideways scrolling", async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 800 });
    await page.goto("/indicators");
    await expect(page.getByRole("status")).toBeVisible();
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth,
    );
    expect(overflow).toBe(false);
  });
});
