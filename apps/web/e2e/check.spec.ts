import AxeBuilder from "@axe-core/playwright";
import {
  expect,
  test,
  type APIRequestContext,
  type Page,
} from "@playwright/test";
import { CHECK_ID, DONE_ID, MISSING_ID } from "./ids";
import { mockApi, mockReports } from "./mock-api";

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

test.describe("the picture a shared link shows", () => {
  const png = async (res: Awaited<ReturnType<APIRequestContext["get"]>>) => {
    expect(res.status()).toBe(200);
    expect(res.headers()["content-type"]).toBe("image/png");
    const bytes = await res.body();
    // The PNG signature, then the width and height in the first (IHDR) chunk.
    expect([...bytes.subarray(0, 8)]).toEqual([
      137, 80, 78, 71, 13, 10, 26, 10,
    ]);
    return { width: bytes.readUInt32BE(16), height: bytes.readUInt32BE(20) };
  };

  test("is a 1200 by 630 PNG of the check, and the page offers it to chat and social apps", async ({
    page,
    request,
  }) => {
    expect(
      await png(await request.get(`/check/${DONE_ID}/opengraph-image`)),
    ).toEqual({ width: 1200, height: 630 });

    await page.goto(`/check/${DONE_ID}`);
    const image = new RegExp(`/check/${DONE_ID}/opengraph-image`);
    for (const tag of [
      'meta[property="og:image"]',
      'meta[name="twitter:image"]',
    ]) {
      await expect(page.locator(tag)).toHaveAttribute("content", image);
    }
    await expect(page.locator('meta[name="twitter:card"]')).toHaveAttribute(
      "content",
      "summary_large_image",
    );
  });

  test("is still a picture, the plain one, for a check that is not there", async ({
    request,
  }) => {
    expect(
      await png(await request.get(`/check/${MISSING_ID}/opengraph-image`)),
    ).toEqual({ width: 1200, height: 630 });
  });
});

test.describe("sharing a check", () => {
  test.use({ permissions: ["clipboard-read", "clipboard-write"] });

  test("copies the link, and a summary with the claim, the verdict and the link", async ({
    page,
  }) => {
    await page.goto(`/check/${DONE_ID}`);
    const share = page.getByRole("region", { name: "Share this check" });
    const clipboard = () => page.evaluate(() => navigator.clipboard.readText());

    await share.getByRole("button", { name: "Copy link" }).click();
    await expect(share.getByRole("status")).toHaveText("Link copied.");
    expect(await clipboard()).toBe(page.url());

    await share.getByRole("button", { name: "Copy summary" }).click();
    await expect(share.getByRole("status")).toHaveText("Summary copied.");
    const summary = await clipboard();
    expect(summary).toContain(
      "“Italy's unemployment rate fell from 11.9% in 2015 to 7.7% in 2023.”",
    );
    expect(summary).toContain("Holds up");
    expect(summary.endsWith(page.url())).toBe(true);
  });
});

test.describe("reporting a wrong match", () => {
  const open = async (page: Page) => {
    await page.goto(`/check/${DONE_ID}`);
    await page.getByRole("button", { name: "Report a wrong match" }).click();
  };

  test("sends the choice, the claim and the note, with no account, and says it was recorded", async ({
    page,
  }) => {
    const sent = await mockReports(page);
    await open(page);
    await page.getByRole("radio", { name: /read wrongly/ }).check();
    await page
      .getByLabel("Add a note (optional)")
      .fill("The period should be 2020.");
    await page.getByRole("button", { name: "Send report" }).click();

    await expect(
      page.getByText("Thank you. Your report was recorded."),
    ).toBeVisible();
    expect(sent).toEqual([
      {
        kind: "wrong_reading",
        claim_index: 0,
        note: "The period should be 2020.",
      },
    ]);
    // Done: the form is gone.
    await expect(page.getByRole("button", { name: "Send report" })).toHaveCount(
      0,
    );
  });

  test("shows why a report was refused and keeps the form", async ({
    page,
  }) => {
    await mockReports(page, "refused");
    await open(page);
    await page.getByRole("button", { name: "Send report" }).click();
    await expect(
      page.locator("[role=alert]:not(#__next-route-announcer__)"),
    ).toContainText("too many reports this hour");
    await expect(
      page.getByRole("button", { name: "Send report" }),
    ).toBeEnabled();
  });

  test("has no accessibility violations with the form open", async ({
    page,
  }) => {
    await open(page);
    await expect(
      page.getByRole("group", { name: "What looks wrong?" }),
    ).toBeVisible();
    const { violations } = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag22aa"])
      .analyze();
    expect(violations).toEqual([]);
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
