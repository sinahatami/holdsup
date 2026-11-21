import { expect, test } from "@playwright/test";
import { axeViolations } from "./axe";

test.describe("the privacy and terms page", () => {
  test("is reached from the footer and from the note under the claim box", async ({
    page,
  }) => {
    await page.goto("/");
    await page
      .getByRole("contentinfo")
      .getByRole("link", { name: "Privacy and terms" })
      .click();
    await expect(page).toHaveURL(/\/privacy$/);
    await expect(
      page.getByRole("heading", { level: 1, name: "Privacy and terms" }),
    ).toBeVisible();

    await page.goto("/");
    await page.getByRole("link", { name: "How your text is handled" }).click();
    await expect(page).toHaveURL(/\/privacy$/);
  });

  test("goes to a section from its contents, and passes an accessibility scan", async ({
    page,
  }) => {
    await page.goto("/privacy");
    const removing = "Removing a check, and your rights";
    await page
      .getByRole("navigation", { name: "On this page" })
      .getByRole("link", { name: removing })
      .click();
    await expect(page).toHaveURL(/\/privacy#remove$/);
    await expect(
      page.getByRole("heading", { level: 2, name: removing }),
    ).toBeInViewport();
    expect(await axeViolations(page)).toEqual([]);
  });
});
