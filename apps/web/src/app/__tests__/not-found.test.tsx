import { render, screen, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import CheckNotFound from "@/app/(site)/check/[id]/not-found";
import NotFound from "@/app/not-found";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

// The site's header and footer have their own tests; here the frame only has to be there.
vi.mock("@/components/templates/site-frame", () => ({
  SiteFrame: ({ children }: { children: ReactNode }) => (
    <div data-testid="site-frame">{children}</div>
  ),
}));

const around = () =>
  within(screen.getByRole("navigation", { name: strings.notFound.orTry }));

describe("the 404 pages", () => {
  it("says the page is missing and offers the way back and the other pages", () => {
    render(<NotFound />);
    // An address that matches no page is drawn outside (site)/layout.tsx, so it brings the
    // header and footer itself.
    expect(
      within(screen.getByTestId("site-frame")).getByRole("heading", {
        level: 1,
        name: strings.notFound.heading,
      }),
    ).toBeInTheDocument();
    expect(screen.getByText(strings.notFound.code)).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: strings.check.back }),
    ).toHaveAttribute("href", routes.home);
    expect(
      around().getByRole("link", { name: strings.nav.canCheck }),
    ).toHaveAttribute("href", routes.indicators);
    expect(
      around().getByRole("link", { name: strings.nav.recent }),
    ).toHaveAttribute("href", routes.recent);
    expect(
      around().getByRole("link", { name: strings.nav.methodology }),
    ).toHaveAttribute("href", routes.methodology);
  });

  it("says the check link points at nothing, with the same ways out", () => {
    render(<CheckNotFound />);
    expect(
      screen.getByRole("heading", {
        level: 1,
        name: strings.check.missing.heading,
      }),
    ).toBeInTheDocument();
    expect(screen.getByText(strings.check.missing.body)).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: strings.check.back }),
    ).toHaveAttribute("href", routes.home);
    expect(around().getAllByRole("link")).toHaveLength(3);
  });
});
