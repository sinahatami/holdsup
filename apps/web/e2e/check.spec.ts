import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { CHECK_ID, DONE_ID, MISSING_ID } from "./ids";
import { mockApi } from "./mock-api";

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
  // The home page stays in the DOM, hidden, after the navigation and its sample
  // receipt carries the same badge, so look inside the result's own article.
  await expect(
    page.getByRole("article").getByText("Holds up", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText(/a fall of 4.34 points/)).toBeVisible();

  await expect(page.getByText(/change\(/)).toBeVisible();
  await page.getByText("Technical details").click();
  await expect(page.getByText("4f556131ab70")).toBeVisible();
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

test.describe("a check's permanent link", () => {
  test("is the receipt in the page itself, not a result fetched by the browser", async ({
    page,
    request,
  }) => {
    // No browser mock here: the server has to read the check from the API on its own.
    const html = await (await request.get(`/check/${DONE_ID}`)).text();
    expect(html).toContain("a fall of 4.34 points");
    expect(html).toContain("4f556131ab70");

    await page.goto(`/check/${DONE_ID}`);
    await expect(
      page.getByRole("article").getByText("Holds up", { exact: true }),
    ).toBeVisible();
    await expect(page.getByText(/a fall of 4.34 points/)).toBeVisible();
    await expect(page.getByText("Reading the claims")).toHaveCount(0);
  });

  test("shows the whole receipt open, from how the claim was read to how to verify it", async ({
    page,
  }) => {
    await page.goto(`/check/${DONE_ID}`);
    for (const name of [
      "How HoldsUp read the claim",
      "The official series",
      "How it was recomputed",
      "What the verdict compared",
      "How to verify it yourself",
    ]) {
      await expect(page.getByRole("heading", { level: 4, name })).toBeVisible();
    }
    // Every figure leads to the data: the link opens the source in a new tab.
    const data = page.getByRole("link", { name: /Open the data/ });
    await expect(data).toHaveAttribute("href", /ec\.europa\.eu\/eurostat/);
    await expect(data).toHaveAttribute("target", "_blank");
    // Claimed beside official, with the gap allowed.
    await expect(page.getByText("±0.17%")).toBeVisible();
    // What each verdict means, with the threshold the result recorded.
    await expect(
      page.getByRole("heading", { level: 2, name: "What the verdicts mean" }),
    ).toBeVisible();
    await expect(
      page.getByText(/in at least 70% of comparable time windows/),
    ).toBeVisible();
  });

  test("names the claim and verdict for a shared link, and stays out of search", async ({
    page,
  }) => {
    await page.goto(`/check/${DONE_ID}`);
    await expect(page).toHaveTitle(
      /^Holds up · “Italy's unemployment rate fell from 11\.9% in 2015 to 7\.7% in 2023\.” · HoldsUp$/,
    );
    await expect(page.locator('meta[name="robots"]')).toHaveAttribute(
      "content",
      "noindex",
    );
    await expect(page.locator('meta[property="og:title"]')).toHaveAttribute(
      "content",
      /^Holds up · /,
    );
  });

  test("says so when it points at no check", async ({ page }) => {
    for (const id of [MISSING_ID, "not-an-id"]) {
      await page.goto(`/check/${id}`);
      await expect(
        page.getByRole("heading", { level: 1, name: "No check at this link" }),
      ).toBeVisible();
      await expect(
        page.getByRole("link", { name: "Check another claim" }).last(),
      ).toBeVisible();
    }
  });
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
  await expect(
    page.getByRole("article").getByText("Holds up", { exact: true }),
  ).toBeVisible();
  await page.getByText("Technical details").click();
  const { violations } = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag22aa"])
    .analyze();
  expect(violations).toEqual([]);
});

test("a receipt opened from its link has no accessibility violations", async ({
  page,
}) => {
  await page.goto(`/check/${DONE_ID}`);
  await expect(
    page.getByRole("article").getByText("Holds up", { exact: true }),
  ).toBeVisible();
  await page.getByText("Technical details").click();
  const { violations } = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag22aa"])
    .analyze();
  expect(violations).toEqual([]);
});

test("a link to no check has no accessibility violations", async ({ page }) => {
  await page.goto(`/check/${MISSING_ID}`);
  await expect(
    page.getByRole("heading", { level: 1, name: "No check at this link" }),
  ).toBeVisible();
  const { violations } = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag22aa"])
    .analyze();
  expect(violations).toEqual([]);
});
