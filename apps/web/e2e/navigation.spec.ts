import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const PAGES = [
  { name: "What it can check", url: /\/indicators$/ },
  { name: "Recent checks", url: /\/recent$/ },
  { name: "Methodology", url: /\/methodology$/ },
  { name: "About", url: /\/about$/ },
];

test.describe("the menu on a phone", () => {
  test.use({ viewport: { width: 360, height: 740 } });

  test("lists every page, and following a link closes it", async ({ page }) => {
    await page.goto("/");
    const toggle = page.getByRole("button", { name: "Open the menu" });
    await expect(toggle).toHaveAttribute("aria-expanded", "false");
    // No page link sits in the header row at this width.
    await expect(
      page.getByRole("navigation", { name: "Main" }).getByRole("link", {
        name: "Methodology",
      }),
    ).toBeHidden();

    await toggle.click();
    const menu = page.getByRole("navigation", { name: "Pages" });
    await expect(menu.getByRole("link")).toHaveText(PAGES.map((p) => p.name));

    await menu.getByRole("link", { name: "About" }).click();
    await expect(page).toHaveURL(/\/about$/);
    await expect(
      page.getByRole("button", { name: "Open the menu" }),
    ).toHaveAttribute("aria-expanded", "false");
    await expect(menu).toBeHidden();
  });

  test("reaches Recent checks and Methodology, which the header row never shows on a phone", async ({
    page,
  }) => {
    for (const { name, url } of PAGES.slice(1, 3)) {
      await page.goto("/");
      await page.getByRole("button", { name: "Open the menu" }).click();
      await page
        .getByRole("navigation", { name: "Pages" })
        .getByRole("link", { name })
        .click();
      await expect(page).toHaveURL(url);
    }
  });

  test("is operated from the keyboard, and Escape closes it", async ({
    page,
  }) => {
    await page.goto("/");
    const toggle = page.getByRole("button", { name: "Open the menu" });
    await toggle.focus();
    await page.keyboard.press("Enter");
    const menu = page.getByRole("navigation", { name: "Pages" });
    await expect(menu).toBeVisible();
    await page.keyboard.press("Tab");
    await expect(menu.getByRole("link").first()).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(menu).toBeHidden();
    await expect(
      page.getByRole("button", { name: "Open the menu" }),
    ).toBeFocused();
  });

  test("fits the screen and passes the accessibility scan while open", async ({
    page,
  }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Open the menu" }).click();
    await expect(page.getByRole("navigation", { name: "Pages" })).toBeVisible();
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - window.innerWidth,
    );
    expect(overflow).toBeLessThanOrEqual(0);
    const { violations } = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag22aa"])
      .analyze();
    expect(violations).toEqual([]);
  });
});

test("on a desktop the header shows the pages and no menu button", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/");
  const main = page.getByRole("navigation", { name: "Main" });
  for (const { name } of PAGES.slice(0, 3))
    await expect(main.getByRole("link", { name })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Open the menu" }),
  ).toBeHidden();
});
