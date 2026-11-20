import { afterEach, describe, expect, it, vi } from "vitest";
import robots from "@/app/robots";
import sitemap from "@/app/sitemap";
import { siteUrl } from "@/lib/site-url";

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("siteUrl", () => {
  it("prefers the configured address, without a trailing slash", () => {
    vi.stubEnv("NEXT_PUBLIC_SITE_URL", "https://example.org/");
    vi.stubEnv("VERCEL_PROJECT_PRODUCTION_URL", "holdsup.vercel.app");
    expect(siteUrl()).toBe("https://example.org");
  });

  it("falls back to Vercel's production domain, then the dev server", () => {
    vi.stubEnv("NEXT_PUBLIC_SITE_URL", "");
    vi.stubEnv("VERCEL_PROJECT_PRODUCTION_URL", "holdsup.vercel.app");
    expect(siteUrl()).toBe("https://holdsup.vercel.app");
    vi.stubEnv("VERCEL_PROJECT_PRODUCTION_URL", "");
    expect(siteUrl()).toBe("http://localhost:3000");
  });
});

describe("robots.txt and the sitemap", () => {
  it("lets crawlers read every page, so they see each receipt's noindex", () => {
    vi.stubEnv("NEXT_PUBLIC_SITE_URL", "https://holdsup.example");
    expect(robots()).toEqual({
      rules: { userAgent: "*", allow: "/" },
      sitemap: "https://holdsup.example/sitemap.xml",
    });
  });

  it("lists the public pages with absolute addresses and no receipts", () => {
    vi.stubEnv("NEXT_PUBLIC_SITE_URL", "https://holdsup.example");
    const urls = sitemap().map((entry) => entry.url);
    expect(urls).toEqual([
      "https://holdsup.example",
      "https://holdsup.example/methodology",
      "https://holdsup.example/indicators",
      "https://holdsup.example/recent",
      "https://holdsup.example/eval",
      "https://holdsup.example/about",
    ]);
    expect(
      urls.some((url) => url.includes("/check/") || url.includes("/embed/")),
    ).toBe(false);
  });
});
