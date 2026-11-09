import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  PAGE_SIZE,
  RecentExplorer,
} from "@/components/organisms/recent-explorer";
import { strings } from "@/lib/strings";
import { galleryClaim, galleryItem } from "@/test/fixtures";

let address = "";
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(address),
}));

const t = strings.recent;
const items = [
  galleryItem({
    id: "it",
    claims: [galleryClaim({ quote: "Italy claim", geo: "IT", theme: "work" })],
  }),
  galleryItem({
    id: "fr",
    claims: [
      galleryClaim({
        quote: "France claim",
        label: "not_supported",
        geo: "FR",
        theme: "health",
      }),
    ],
  }),
  galleryItem({
    id: "de",
    claims: [
      galleryClaim({ quote: "Germany claim", geo: "DE", theme: "work" }),
      galleryClaim({
        quote: "EU claim",
        label: "partly_supported",
        geo: "EU",
        theme: "economy",
      }),
    ],
  }),
];

const status = () => screen.getByRole("status").textContent;
// Each check is one link to its receipt; a card with several claims has lists inside, so
// counting list items would count claims too.
const cards = () =>
  screen
    .queryAllByRole("link")
    .filter((a) => a.getAttribute("href")?.startsWith("/check/"))
    .map((a) => a.textContent ?? "");
const button = (name: RegExp) => screen.getByRole("button", { name });

beforeEach(() => {
  address = "";
  window.history.replaceState(null, "", "/recent");
});
afterEach(() => window.history.replaceState(null, "", "/"));

describe("RecentExplorer", () => {
  it("lists every check, newest first, and says how many", () => {
    render(<RecentExplorer items={items} />);
    expect(status()).toBe("Showing 3 of 3 checks");
    expect(cards()).toHaveLength(3);
    expect(cards()[0]).toContain("Italy claim");
  });

  it("filters by verdict with buttons that say which is on", () => {
    render(<RecentExplorer items={items} />);
    fireEvent.click(button(/^Does not hold up/));
    expect(button(/^Does not hold up/)).toHaveAttribute("aria-pressed", "true");
    expect(cards()).toHaveLength(1);
    expect(cards()[0]).toContain("France claim");
    expect(status()).toBe("Showing 1 of 1 matching checks (3 in all)");
    fireEvent.click(button(/^Does not hold up/));
    expect(cards()).toHaveLength(3);
  });

  it("filters by topic and by place together", () => {
    render(<RecentExplorer items={items} />);
    fireEvent.click(button(/^Work and pay/));
    expect(cards()).toHaveLength(2);
    fireEvent.change(screen.getByLabelText(t.place), {
      target: { value: "DE" },
    });
    expect(cards()).toHaveLength(1);
    expect(cards()[0]).toContain("Germany claim");
  });

  it("counts each choice under the other filters and turns off those with nothing", () => {
    render(<RecentExplorer items={items} />);
    fireEvent.click(button(/^Work and pay/));
    expect(button(/^Does not hold up/)).toBeDisabled();
    expect(button(/^Partly holds up/)).toHaveTextContent("1");
    expect(button(/^Holds up(?!,)/)).toHaveTextContent("2");
  });

  it("offers the places the checks are about, A to Z by name", () => {
    render(<RecentExplorer items={items} />);
    const options = screen.getAllByRole("option").map((o) => o.textContent);
    expect(options).toEqual([
      t.anyPlace,
      "European Union",
      "France",
      "Germany",
      "Italy",
    ]);
  });

  it("explains an empty result and clears it", () => {
    render(<RecentExplorer items={items} />);
    fireEvent.click(button(/^Does not hold up/));
    fireEvent.change(screen.getByLabelText(t.place), {
      target: { value: "DE" },
    });
    expect(screen.getByText(t.none)).toBeInTheDocument();
    expect(screen.getByText(t.noneHint)).toBeInTheDocument();
    expect(cards()).toHaveLength(0);
    expect(status()).toBe("Showing 0 of 0 matching checks (3 in all)");
    fireEvent.click(button(new RegExp(t.clear)));
    expect(cards()).toHaveLength(3);
    expect(screen.getByLabelText(t.place)).toHaveValue("");
    expect(window.location.search).toBe("");
  });

  it("writes the filter to the address, and opens filtered from a link", () => {
    const { unmount } = render(<RecentExplorer items={items} />);
    fireEvent.click(button(/^Work and pay/));
    expect(window.location.search).toBe("?theme=work");
    unmount();
    address = "verdict=not_supported&place=FR";
    render(<RecentExplorer items={items} />);
    expect(cards()).toHaveLength(1);
    expect(screen.getByLabelText(t.place)).toHaveValue("FR");
  });
});

describe("paging", () => {
  const many = Array.from({ length: PAGE_SIZE * 2 + 3 }, (_, i) =>
    galleryItem({
      id: `c${i}`,
      claims: [
        galleryClaim({
          quote: `Claim ${i}`,
          label: i % 2 ? "supported" : "not_supported",
        }),
      ],
    }),
  );

  it("shows a page at a time and adds one each time it is asked", () => {
    render(<RecentExplorer items={many} />);
    expect(cards()).toHaveLength(PAGE_SIZE);
    expect(status()).toBe(`Showing ${PAGE_SIZE} of ${many.length} checks`);
    fireEvent.click(button(new RegExp(t.showMore)));
    expect(cards()).toHaveLength(PAGE_SIZE * 2);
    fireEvent.click(button(new RegExp(t.showMore)));
    expect(cards()).toHaveLength(many.length);
    expect(
      screen.queryByRole("button", { name: t.showMore }),
    ).not.toBeInTheDocument();
  });

  it("starts again from the first page when the filter changes", () => {
    render(<RecentExplorer items={many} />);
    fireEvent.click(button(new RegExp(t.showMore)));
    expect(cards()).toHaveLength(PAGE_SIZE * 2);
    fireEvent.click(button(/^Holds up(?!,)/));
    expect(cards().length).toBeLessThanOrEqual(PAGE_SIZE);
  });
});
