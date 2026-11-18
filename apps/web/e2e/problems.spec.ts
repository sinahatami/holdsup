import { expect, test } from "@playwright/test";
import { axeViolations } from "./axe";
import { CAPACITY_ID, CHECK_ID } from "./ids";
import { mockApi } from "./mock-api";

const alert = (page: import("@playwright/test").Page) =>
  page.locator("[role=alert]:not(#__next-route-announcer__)");

test.describe("when something goes wrong", () => {
  test("a lost connection is said under the header, and goes away when it is back", async ({
    page,
    context,
  }) => {
    await page.goto("/");
    await expect(alert(page)).toHaveCount(0);
    await context.setOffline(true);
    await expect(alert(page)).toContainText("You are offline");
    await context.setOffline(false);
    await expect(alert(page)).toHaveCount(0);
  });

  test("a submission that cannot reach HoldsUp says so, and pressing again sends it", async ({
    page,
  }) => {
    await mockApi(page);
    // Registered after the mock, so it runs first: the first send fails, later ones go on.
    let sends = 0;
    await page.route("http://api.test/v1/checks", (route) => {
      if (route.request().method() !== "POST") return route.fallback();
      sends += 1;
      return sends === 1 ? route.abort("failed") : route.fallback();
    });
    await page.goto("/");
    await page.getByLabel("The claim to check").fill("Rents rose 5% in 2023.");
    await page.getByRole("button", { name: "Check this claim" }).click();
    await expect(alert(page)).toContainText("could not be reached");
    // The text is still in the box and the button is ready: nothing to retype.
    await expect(page.getByLabel("The claim to check")).toHaveValue(
      "Rents rose 5% in 2023.",
    );
    await page.getByRole("button", { name: "Check this claim" }).click();
    await expect(page).toHaveURL(new RegExp(`/check/${CHECK_ID}$`));
    expect(sends).toBe(2);
  });

  test("a failed check names the failure, and its retry button waits out the time the API gave", async ({
    page,
  }) => {
    await mockApi(page, "error");
    await page.goto(`/check/${CHECK_ID}`);
    await expect(
      page.getByRole("heading", {
        name: "HoldsUp could not finish this check",
      }),
    ).toBeVisible();
    // The mock says to wait 30 seconds.
    const retry = page.getByRole("button", { name: /^Try again in \d+ s$/ });
    await expect(retry).toBeVisible();
    await expect(retry).toBeDisabled();
  });
});

test.describe("at capacity", () => {
  // Every model provider busy: the page says when HoldsUp is back (once, in minutes), the
  // retry waits that long, and checks done earlier fill the wait. Checked at phone width.
  async function expectAtCapacity(page: import("@playwright/test").Page) {
    await expect(
      page.getByRole("heading", { name: "HoldsUp is at capacity" }),
    ).toBeVisible();
    await expect(alert(page)).toContainText("Back in about 10 minutes.");
    await expect(alert(page)).not.toContainText("seconds");
    await expect(
      page.getByRole("button", { name: "Try again in 10 min" }),
    ).toBeDisabled();
    const waiting = page.getByRole("region", { name: "While you wait" });
    // Four cards (each card lists its own claims inside it, so count the cards only).
    await expect(
      waiting.locator("ul").first().locator(":scope > li"),
    ).toHaveCount(4);
    await expect(
      waiting.getByRole("link", { name: "See all recent checks" }),
    ).toHaveAttribute("href", "/recent");
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - window.innerWidth,
    );
    expect(overflow).toBeLessThanOrEqual(0);
    expect(await axeViolations(page)).toEqual([]);
  }

  test("a live check that finds every provider busy says when HoldsUp is back and shows checks done earlier", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 360, height: 740 });
    await mockApi(page, "at-capacity");
    await page.goto(`/check/${CHECK_ID}`);
    await expectAtCapacity(page);
  });

  test("the link of a check that failed at capacity shows the same, drawn by the server", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 360, height: 740 });
    await page.goto(`/check/${CAPACITY_ID}`);
    await expectAtCapacity(page);
  });
});

test.describe("a page that does not exist", () => {
  test("is a 404 that keeps the header and footer and points to the main pages", async ({
    page,
  }) => {
    const response = await page.goto("/no-such-page");
    expect(response?.status()).toBe(404);
    await expect(
      page.getByRole("heading", { level: 1, name: "Page not found" }),
    ).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Main" })).toBeVisible();
    const around = page.getByRole("navigation", { name: "Or look at" });
    for (const name of ["What it can check", "Recent checks", "Methodology"])
      await expect(around.getByRole("link", { name })).toBeVisible();
    await page.getByRole("link", { name: "Check another claim" }).click();
    await expect(page).toHaveURL(/\/$/);
  });

  test("fits a 360px screen and passes the accessibility scan", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 360, height: 740 });
    await page.goto("/no-such-page");
    await expect(
      page.getByRole("heading", { level: 1, name: "Page not found" }),
    ).toBeVisible();
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - window.innerWidth,
    );
    expect(overflow).toBeLessThanOrEqual(0);
    const violations = await axeViolations(page);
    expect(violations).toEqual([]);
  });
});
