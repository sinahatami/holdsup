import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Tooltip } from "@/components/atoms/tooltip";
import { ThemeToggle } from "@/components/molecules/theme-toggle";
import { strings } from "@/lib/strings";

function button() {
  render(
    <Tooltip label="Back to top">
      <button type="button" aria-label="Back to top">
        ↑
      </button>
    </Tooltip>,
  );
  return screen.getByRole("button", { name: "Back to top" });
}

describe("Tooltip", () => {
  it("repeats the control's name for sighted readers, hidden from assistive technology", () => {
    const control = button();
    const tip = screen.getByTestId("tooltip");
    expect(tip).toHaveTextContent("Back to top");
    expect(tip).toHaveAttribute("aria-hidden", "true");
    // The control's name is its own, so a screen reader says it once.
    expect(control).toHaveAccessibleName("Back to top");
    expect(control).not.toHaveAccessibleDescription();
  });

  it("is hidden by Escape until the focus or the pointer leaves", () => {
    const control = button();
    const wrapper = control.parentElement!;
    fireEvent.keyDown(control, { key: "Escape" });
    expect(wrapper).toHaveAttribute("data-dismissed", "true");
    fireEvent.blur(control);
    expect(wrapper).not.toHaveAttribute("data-dismissed");
    fireEvent.keyDown(control, { key: "Escape" });
    fireEvent.pointerLeave(wrapper);
    expect(wrapper).not.toHaveAttribute("data-dismissed");
  });

  it("replaces the browser's own title tooltip on the icon-only theme buttons", () => {
    render(<ThemeToggle />);
    for (const name of [
      strings.nav.themeLight,
      strings.nav.themeSystem,
      strings.nav.themeDark,
    ]) {
      const radio = screen.getByRole("radio", { name });
      expect(radio).not.toHaveAttribute("title");
      expect(radio.parentElement).toHaveTextContent(name);
    }
  });
});
