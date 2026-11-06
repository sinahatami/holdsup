import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Home from "@/app/page";
import { strings } from "@/lib/strings";

describe("Home page", () => {
  it("renders the app name and tagline", () => {
    render(<Home />);
    expect(
      screen.getByRole("heading", { level: 1, name: strings.appName }),
    ).toBeInTheDocument();
    expect(screen.getByText(strings.tagline)).toBeInTheDocument();
  });
});
