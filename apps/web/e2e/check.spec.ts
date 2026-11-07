import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { CHECK_ID, mockApi } from "./mock-api";

test("submit → trace → result", async ({ page }) => {
  await mockApi(page);
  await page.goto("/");
  await expect(
    page.getByRole("heading", { level: 1, name: "HoldsUp" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: /Italy's unemployment rate fell/ })
    .click();
  await page.getByRole("button", { name: "Check this claim" }).click();

  await expect(page).toHaveURL(new RegExp(`/check/${CHECK_ID}$`));
  await expect(page.getByText("Reading the claims")).toBeVisible();
  await expect(page.getByText("Holds up", { exact: true })).toBeVisible();
  await expect(page.getByText(/a fall of 4.2 points/)).toBeVisible();

  await page.getByText("Receipt", { exact: true }).click();
  await expect(page.getByText("9f2c0de1")).toBeVisible();
  await expect(page.getByText(/change\(/)).toBeVisible();
});

test("a failed check shows the problem and when to retry", async ({ page }) => {
  await mockApi(page, "error");
  await page.goto(`/check/${CHECK_ID}`);
  await expect(
    page.locator("[role=alert]:not(#__next-route-announcer__)"),
  ).toContainText("All model providers are busy.");
  await expect(
    page.locator("[role=alert]:not(#__next-route-announcer__)"),
  ).toContainText("30 seconds");
});

test("a refused submission shows the reason on the home page", async ({
  page,
}) => {
  await mockApi(page, "rate-limit");
  await page.goto("/");
  await page.getByLabel("The claim to check").fill("Some claim 5%.");
  await page.getByRole("button", { name: "Check this claim" }).click();
  await expect(
    page.locator("[role=alert]:not(#__next-route-announcer__)"),
  ).toContainText("hourly limit");
});

test("home page has no accessibility violations", async ({ page }) => {
  await page.goto("/");
  const { violations } = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag22aa"])
    .analyze();
  expect(violations).toEqual([]);
});

test("result page has no accessibility violations", async ({ page }) => {
  await mockApi(page);
  await page.goto(`/check/${CHECK_ID}`);
  await expect(page.getByText("Holds up", { exact: true })).toBeVisible();
  await page.getByText("Receipt", { exact: true }).click();
  const { violations } = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag22aa"])
    .analyze();
  expect(violations).toEqual([]);
});
