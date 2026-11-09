import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { HeaderLinks } from "@/components/molecules/header-links";

const path = vi.hoisted(() => ({ current: "/" }));
vi.mock("next/navigation", () => ({ usePathname: () => path.current }));

const links = [
  { href: "/indicators", label: "What it can check" },
  { href: "/methodology", label: "Methodology" },
  { href: "/about", label: "About" },
];

beforeEach(() => {
  path.current = "/";
});

describe("HeaderLinks", () => {
  it("lists every page as a link, none marked on the home page", () => {
    render(<HeaderLinks links={links} />);
    expect(screen.getAllByRole("link").map((a) => a.textContent)).toEqual(
      links.map((l) => l.label),
    );
    for (const link of screen.getAllByRole("link")) {
      expect(link).not.toHaveAttribute("aria-current");
    }
  });

  it("marks only the page you are on", () => {
    path.current = "/methodology";
    render(<HeaderLinks links={links} />);
    expect(screen.getByRole("link", { name: "Methodology" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("link", { name: "About" })).not.toHaveAttribute(
      "aria-current",
    );
  });
});
