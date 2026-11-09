import { screen } from "@testing-library/react";
import { expect } from "vitest";
import { strings } from "@/lib/strings";

/**
 * The link to a page off the site: its spoken name ends with the new-tab note, and it
 * opens in a new tab without handing the page over to the one it opens.
 */
export function externalLink(label: string, href: string) {
  const link = screen.getByRole("link", {
    name: `${label} ${strings.receipt.opensInNewTab}`,
  });
  expect(link).toHaveAttribute("href", href);
  expect(link).toHaveAttribute("target", "_blank");
  expect(link).toHaveAttribute("rel", expect.stringContaining("noopener"));
  return link;
}
