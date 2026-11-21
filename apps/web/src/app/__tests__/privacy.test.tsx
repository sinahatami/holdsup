import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Page, { metadata } from "@/app/(site)/privacy/page";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";
import { pageStrings } from "@/lib/strings/pages";
import { externalLink } from "@/test/external";

const t = pageStrings.privacy;

const SECTIONS = [
  t.kept.heading,
  t.who.heading,
  t.address.heading,
  t.browser.heading,
  t.basis.heading,
  t.remove.heading,
  t.terms.heading,
  t.changes.heading,
];

describe("Privacy and terms page", () => {
  it("has a title, the date it was last changed, and a summary", () => {
    render(<Page />);
    expect(
      screen.getByRole("heading", { level: 1, name: t.heading }),
    ).toBeInTheDocument();
    const date = screen.getByText(t.updated.text);
    expect(date.tagName).toBe("TIME");
    expect(date).toHaveAttribute("dateTime", t.updated.iso);
    const glance = screen.getByRole("list", { name: t.glanceLabel });
    expect(within(glance).getAllByRole("listitem")).toHaveLength(
      t.glance.length,
    );
  });

  it("lists every section, and each link lands on its heading", () => {
    render(<Page />);
    expect(
      screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent),
    ).toEqual(SECTIONS);
    const contents = screen.getByRole("navigation", { name: t.onThisPage });
    for (const link of within(contents).getAllByRole("link")) {
      const id = link.getAttribute("href")!.slice(1);
      const section = document.getElementById(id);
      expect(section).not.toBeNull();
      expect(section).toHaveAccessibleName(link.textContent!);
    }
  });

  it("names every outside service that handles the text, with its privacy policy", () => {
    render(<Page />);
    for (const group of t.who.groups) {
      expect(
        screen.getByRole("heading", { level: 3, name: group.title }),
      ).toBeInTheDocument();
      for (const service of group.services)
        externalLink(service.name, service.url);
    }
  });

  it("explains how to have a check removed, with a way to ask for anything else", () => {
    render(<Page />);
    const section = document.getElementById("remove")!;
    const steps = within(section).getAllByRole("listitem");
    expect(steps).toHaveLength(t.remove.steps.length);
    t.remove.steps.forEach((step, i) =>
      expect(steps[i]).toHaveTextContent(step),
    );
    // The steps name the controls exactly as the check page shows them.
    expect(t.remove.steps[0]).toContain(strings.report.open);
    expect(t.remove.steps[1]).toContain(strings.report.kinds.remove);
    externalLink(t.remove.issue, strings.footer.issuesUrl);
  });

  it("links the terms to the sources and the licence", () => {
    render(<Page />);
    expect(screen.getByRole("link", { name: t.terms.sources })).toHaveAttribute(
      "href",
      `${routes.about}#data`,
    );
    externalLink(t.terms.license, strings.footer.licenseUrl);
    externalLink(t.changes.history, t.changes.historyUrl);
  });

  it("has its own title and canonical address", () => {
    expect(metadata.title).toBe(`${t.meta.title} · ${strings.appName}`);
    expect(metadata.alternates?.canonical).toBe(routes.privacy);
  });
});
