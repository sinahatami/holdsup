import { describe, expect, it } from "vitest";
import { asLink, siteName, webUrl } from "@/lib/link";

describe("asLink", () => {
  it.each([
    ["https://example.com/news/jobs", "https://example.com/news/jobs"],
    ["  HTTP://Example.com/a?b=1  ", "HTTP://Example.com/a?b=1"],
    ["www.example.com/story", "https://www.example.com/story"],
  ])("reads %j as a link", (text, link) => {
    expect(asLink(text)).toBe(link);
  });

  it.each([
    "Italy's unemployment fell to 7.7%.",
    "see https://example.com for more",
    "www.",
    "ftp://example.com/file",
    "",
    `https://example.com/${"x".repeat(2000)}`,
  ])("reads %j as text", (text) => {
    expect(asLink(text)).toBeNull();
  });
});

describe("webUrl and siteName", () => {
  it("keeps only http and https addresses as hrefs", () => {
    expect(webUrl("https://news.example/a")).toBe("https://news.example/a");
    expect(webUrl("http://news.example/a")).toBe("http://news.example/a");
    expect(webUrl("javascript:alert(1)")).toBeNull();
    expect(webUrl("not a url")).toBeNull();
  });

  it("names the site without www", () => {
    expect(siteName("https://www.news.example/a/b?c")).toBe("news.example");
    expect(siteName("odd")).toBe("odd");
    expect(siteName("javascript:alert(1)")).toBe("javascript:alert(1)");
  });
});
