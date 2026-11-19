import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Logo } from "@/components/atoms/logo";
import { LogoLockup } from "@/components/atoms/logo-lockup";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

describe("Logo", () => {
  it("is the home link, named once: the drawing inside it is decoration", () => {
    const { container } = render(<Logo variant="badge" />);
    expect(screen.getByRole("link", { name: strings.appName })).toHaveAttribute(
      "href",
      routes.home,
    );
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(container.querySelector("svg")).toHaveAttribute(
      "aria-hidden",
      "true",
    );
  });
});

describe("LogoLockup", () => {
  it("is an image of the name when it stands alone", () => {
    render(<LogoLockup label={strings.appName} />);
    expect(
      screen.getByRole("img", { name: strings.appName }),
    ).toBeInTheDocument();
  });

  it("draws the denominator in the record blue and the rest in the text colour", () => {
    const { container } = render(<LogoLockup />);
    expect(container.querySelector("path")).toHaveAttribute(
      "fill",
      "currentColor",
    );
    expect(container.querySelector("circle")).toHaveClass("fill-brand");
  });
});
