import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SiteFooter } from "@/components/organisms/site-footer";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";
import { APP_VERSION } from "@/lib/version";
import { externalLink } from "@/test/external";

const t = strings.footer;

describe("SiteFooter", () => {
  it("lists the pages in one group and the project in another", () => {
    render(<SiteFooter />);
    const explore = screen.getByRole("navigation", { name: t.explore });
    const hrefs = within(explore)
      .getAllByRole("link")
      .map((a) => a.getAttribute("href"));
    expect(hrefs).toEqual([
      routes.indicators,
      routes.recent,
      routes.methodology,
    ]);
    const project = screen.getByRole("navigation", { name: t.project });
    expect(
      within(project).getByRole("link", { name: strings.nav.about }),
    ).toHaveAttribute("href", routes.about);
  });

  it("links to the repository, the issues and the licence", () => {
    render(<SiteFooter />);
    externalLink(t.github, t.repoUrl);
    externalLink(t.report, t.issuesUrl);
    externalLink(t.license, t.licenseUrl);
  });

  it("names the release it runs and links to that release's notes", () => {
    render(<SiteFooter />);
    expect(APP_VERSION).toMatch(/^\d+\.\d+\.\d+$/);
    const link = externalLink(
      `${t.releaseNotes} ${t.version(APP_VERSION)}`,
      t.releaseUrl(APP_VERSION),
    );
    expect(link).toHaveTextContent(`v${APP_VERSION}`);
    expect(link).toHaveAttribute(
      "href",
      `https://github.com/sinahatami/holdsup/releases/tag/v${APP_VERSION}`,
    );
  });

  it("does not repeat Home, which the logo already is", () => {
    render(<SiteFooter />);
    expect(
      screen.queryByRole("link", { name: strings.nav.home }),
    ).not.toBeInTheDocument();
  });
});
