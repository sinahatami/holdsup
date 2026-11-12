import { expect, test } from "@playwright/test";
import { axeViolations } from "./axe";
import { CHECK_ID } from "./ids";
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
