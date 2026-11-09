import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MobileNav } from "@/components/molecules/mobile-nav";
import { SiteHeader } from "@/components/organisms/site-header";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

const path = vi.hoisted(() => ({ current: "/" }));
vi.mock("next/navigation", () => ({ usePathname: () => path.current }));

const links = [
  { href: "/indicators", label: "What it can check" },
  { href: "/methodology", label: "Methodology" },
  { href: "/about", label: "About" },
];

const t = strings.nav;
const toggle = () => screen.getByRole("button", { name: /the menu$/ });
// The panel is hidden while closed, so look it up by its id, not by role.
const panel = () => document.getElementById("mobile-nav-panel")!;

beforeEach(() => {
  path.current = "/";
});

describe("MobileNav", () => {
  it("starts closed, with the pages out of reach", () => {
    render(<MobileNav links={links} />);
    expect(toggle()).toHaveAttribute("aria-expanded", "false");
    expect(toggle()).toHaveAccessibleName(t.menuOpen);
    expect(panel()).toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  it("opens to list every page as a link and closes on a second press", () => {
    render(<MobileNav links={links} />);
    fireEvent.click(toggle());
    expect(toggle()).toHaveAttribute("aria-expanded", "true");
    expect(toggle()).toHaveAccessibleName(t.menuClose);
    expect(screen.getAllByRole("link").map((a) => a.textContent)).toEqual(
      links.map((l) => l.label),
    );
    expect(screen.getByRole("link", { name: "About" })).toHaveAttribute(
      "href",
      "/about",
    );
    fireEvent.click(toggle());
    expect(toggle()).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  it("marks the page you are on", () => {
    path.current = "/methodology";
    render(<MobileNav links={links} />);
    fireEvent.click(toggle());
    expect(screen.getByRole("link", { name: "Methodology" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("link", { name: "About" })).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("closes on Escape and gives focus back to the button", () => {
    render(<MobileNav links={links} />);
    fireEvent.click(toggle());
    fireEvent.keyDown(document, { key: "Escape" });
    expect(toggle()).toHaveAttribute("aria-expanded", "false");
    expect(toggle()).toHaveFocus();
  });

  it("closes by itself when the page changes", () => {
    const { rerender } = render(<MobileNav links={links} />);
    fireEvent.click(toggle());
    expect(toggle()).toHaveAttribute("aria-expanded", "true");
    path.current = "/about";
    rerender(<MobileNav links={links} />);
    expect(toggle()).toHaveAttribute("aria-expanded", "false");
  });
});

describe("SiteHeader", () => {
  it("offers every page in the menu, including About, which the header row leaves out", () => {
    render(<SiteHeader />);
    fireEvent.click(toggle());
    const menu = within(panel());
    for (const label of [t.canCheck, t.recent, t.methodology, t.about])
      expect(menu.getByRole("link", { name: label })).toBeInTheDocument();
    expect(menu.getByRole("link", { name: t.recent })).toHaveAttribute(
      "href",
      routes.recent,
    );
  });
});
