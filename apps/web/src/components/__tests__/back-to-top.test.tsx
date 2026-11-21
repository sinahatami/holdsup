import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { BackToTop } from "@/components/molecules/back-to-top";
import { strings } from "@/lib/strings";

function scrollTo(y: number) {
  Object.defineProperty(window, "scrollY", { value: y, configurable: true });
  act(() => {
    window.dispatchEvent(new Event("scroll"));
  });
}

function reducedMotion(reduce: boolean) {
  window.matchMedia = vi.fn().mockReturnValue({ matches: reduce });
}

const button = () =>
  screen.queryByRole("button", { name: strings.nav.backToTop });

describe("BackToTop", () => {
  beforeEach(() => {
    Object.defineProperty(window, "innerHeight", {
      value: 800,
      configurable: true,
    });
    window.scrollTo = vi.fn();
    reducedMotion(false);
  });
  afterEach(() => scrollTo(0));

  it("stays out of the page until the reader is a screen down", () => {
    render(<BackToTop />);
    expect(button()).toBeNull();
    scrollTo(800);
    expect(button()).toBeNull();
    scrollTo(801);
    expect(button()).toBeInTheDocument();
    scrollTo(10);
    expect(button()).toBeNull();
  });

  it("scrolls to the top smoothly and hands focus to the header's first link", () => {
    render(
      <>
        <header>
          <a href="#top">{strings.appName}</a>
        </header>
        <BackToTop />
      </>,
    );
    scrollTo(2000);
    fireEvent.click(button()!);
    expect(window.scrollTo).toHaveBeenCalledWith({
      top: 0,
      behavior: "smooth",
    });
    expect(screen.getByRole("link", { name: strings.appName })).toHaveFocus();
  });

  it("jumps without animation when the reader asks for reduced motion", () => {
    reducedMotion(true);
    render(<BackToTop />);
    scrollTo(2000);
    fireEvent.click(button()!);
    expect(window.scrollTo).toHaveBeenCalledWith({ top: 0, behavior: "auto" });
  });
});
