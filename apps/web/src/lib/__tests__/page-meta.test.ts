import { describe, expect, it } from "vitest";
import { pageMetadata } from "@/lib/page-meta";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

describe("pageMetadata", () => {
  it("gives the page its own canonical and Open Graph address", () => {
    const m = pageMetadata({
      path: routes.methodology,
      title: "Methodology · HoldsUp",
      description: "How it works.",
    });
    expect(m).toEqual({
      title: "Methodology · HoldsUp",
      description: "How it works.",
      alternates: { canonical: "/methodology" },
      openGraph: {
        type: "website",
        siteName: strings.appName,
        url: "/methodology",
        title: "Methodology · HoldsUp",
        description: "How it works.",
      },
    });
  });

  it("leaves the description to the site's when a page has none", () => {
    const m = pageMetadata({ path: routes.indicators, title: "Indicators" });
    expect(m).not.toHaveProperty("description");
    expect(m.openGraph).not.toHaveProperty("description");
    expect(m.alternates).toEqual({ canonical: "/indicators" });
  });
});
