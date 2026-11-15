import { expect, test } from "@playwright/test";
import { axeViolations } from "./axe";

test.describe("the how-it-compares page", () => {
  test("is reached from the footer and shows the head-to-head", async ({
    page,
  }) => {
    await page.goto("/");
    await page
      .getByRole("contentinfo")
      .getByRole("link", { name: "How it compares" })
      .click();
    await expect(page).toHaveURL(/\/eval$/);
    await expect(
      page.getByRole("heading", { level: 1, name: "How it compares" }),
    ).toBeVisible();
    const table = page.getByRole("table", {
      name: /Verdict accuracy on the development claims/,
    });
    await expect(table.getByRole("row", { name: /HoldsUp/ })).toContainText(
      "75.0%",
    );
    await expect(
      table.getByRole("row", { name: /Plain chatbot/ }),
    ).toContainText("54.2%");
  });

  test("lists where HoldsUp loses and why it is wrong", async ({ page }) => {
    await page.goto("/eval");
    const losses = page.getByRole("table", {
      name: "Claims HoldsUp got wrong and the chatbot got right",
    });
    await expect(losses).toContainText("Rents went up 40% in five years");
    await expect(losses).toContainText("Choosing the statistic");
    await expect(
      page.getByRole("heading", { name: "Why HoldsUp is wrong" }),
    ).toBeVisible();
    await expect(
      page.getByText("Choosing the statistic: 6 wrong"),
    ).toBeVisible();
  });

  test("has no accessibility violations", async ({ page }) => {
    await page.goto("/eval");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    expect(await axeViolations(page)).toEqual([]);
  });

  test("fits a 360px screen: the tables scroll, the page does not", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 360, height: 800 });
    await page.goto("/eval");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    const overflow = await page.evaluate(
      () =>
        document.documentElement.scrollWidth >
        document.documentElement.clientWidth,
    );
    expect(overflow).toBe(false);
  });
});
