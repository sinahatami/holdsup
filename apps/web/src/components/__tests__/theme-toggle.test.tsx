import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { ThemeToggle } from "@/components/molecules/theme-toggle";
import { THEME_KEY } from "@/lib/theme";
import { strings } from "@/lib/strings";

describe("ThemeToggle", () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => document.documentElement.classList.remove("dark", "light"));

  it("is a named group of three named choices, with the current one marked", () => {
    render(<ThemeToggle />);
    const group = screen.getByRole("radiogroup", { name: strings.nav.theme });
    const names = ["themeLight", "themeSystem", "themeDark"] as const;
    const radios = screen.getAllByRole("radio");
    // Icons only on screen, so each choice is named for assistive technology.
    expect(radios.map((r) => r.getAttribute("aria-label"))).toEqual(
      names.map((n) => strings.nav[n]),
    );
    expect(group).toContainElement(radios[0]);
    // "System" is the starting choice; exactly one is checked at any time.
    expect(radios.map((r) => r.getAttribute("aria-checked"))).toEqual([
      "false",
      "true",
      "false",
    ]);
  });

  it("marks the chosen theme and applies it", () => {
    render(<ThemeToggle />);
    fireEvent.click(screen.getByRole("radio", { name: strings.nav.themeDark }));
    expect(
      screen.getByRole("radio", { name: strings.nav.themeDark }),
    ).toHaveAttribute("aria-checked", "true");
    expect(
      screen.getByRole("radio", { name: strings.nav.themeSystem }),
    ).toHaveAttribute("aria-checked", "false");
    expect(document.documentElement).toHaveClass("dark");
    expect(localStorage.getItem(THEME_KEY)).toBe("dark");

    fireEvent.click(
      screen.getByRole("radio", { name: strings.nav.themeLight }),
    );
    expect(document.documentElement).toHaveClass("light");
    expect(document.documentElement).not.toHaveClass("dark");
  });
});
