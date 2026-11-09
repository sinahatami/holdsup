import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CatalogExplorer } from "@/components/organisms/catalog-explorer";
import { strings } from "@/lib/strings";
import { catalogEntry } from "@/test/fixtures";

let address = "";
vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(address),
}));

const entries = [
  catalogEntry({
    id: "rent",
    name: "Rent prices",
    theme: "prices",
    definition: "How much tenants pay.",
    first_year: 2005,
    last_year: 2022,
  }),
  catalogEntry({
    id: "unemployment",
    name: "Unemployment rate",
    theme: "work",
    source: "the World Bank",
    countries: [],
    groups: ["WORLD"],
    all_countries: true,
    first_year: 1991,
  }),
  catalogEntry({
    id: "poverty",
    name: "At-risk-of-poverty rate",
    theme: "poverty",
    countries: ["IT", "NO"],
    first_year: 1995,
  }),
];

const t = strings.indicators;
const shown = () => screen.getByRole("status").textContent;
const names = () =>
  screen.queryAllByRole("heading", { level: 3 }).map((h) => h.textContent);
const type = (label: string, value: string) =>
  fireEvent.change(screen.getByLabelText(label), { target: { value } });

beforeEach(() => {
  address = "";
  window.history.replaceState(null, "", "/indicators");
});
afterEach(() => window.history.replaceState(null, "", "/"));

describe("CatalogExplorer", () => {
  it("starts with everything, A to Z within each topic", () => {
    render(<CatalogExplorer entries={entries} />);
    expect(shown()).toBe("3 statistics");
    expect(names()).toEqual([
      "Unemployment rate",
      "Rent prices",
      "At-risk-of-poverty rate",
    ]);
    expect(
      screen.queryByRole("button", { name: t.clear }),
    ).not.toBeInTheDocument();
  });

  it("searches by a word, and says how many it found", () => {
    render(<CatalogExplorer entries={entries} />);
    type(t.search, "rate");
    expect(shown()).toBe("2 of 3 statistics");
    expect(names()).toEqual(["Unemployment rate", "At-risk-of-poverty rate"]);
  });

  it("filters by topic with buttons that say which is on", () => {
    render(<CatalogExplorer entries={entries} />);
    fireEvent.click(
      screen.getByRole("button", { name: /^Prices and housing/ }),
    );
    expect(
      screen.getByRole("button", { name: /^Prices and housing/ }),
    ).toHaveAttribute("aria-pressed", "true");
    expect(names()).toEqual(["Rent prices"]);
    fireEvent.click(
      screen.getByRole("button", { name: /^Prices and housing/ }),
    );
    expect(names()).toHaveLength(3);
  });

  it("counts each topic under the other filters, and turns off topics with nothing", () => {
    render(<CatalogExplorer entries={entries} />);
    type(t.search, "rate");
    const prices = screen.getByRole("button", { name: /^Prices and housing/ });
    expect(prices).toBeDisabled();
    expect(
      screen.getByRole("button", { name: /^Work and pay/ }),
    ).toHaveTextContent("1");
  });

  it("filters by place: groups, countries, and countries only a worldwide series covers", () => {
    render(<CatalogExplorer entries={entries} />);
    type(t.place, "NO");
    expect(names()).toEqual(["Unemployment rate", "At-risk-of-poverty rate"]);
    type(t.place, "WORLD");
    expect(names()).toEqual(["Unemployment rate"]);
    type(t.place, "EU");
    expect(names()).toEqual(["Rent prices", "At-risk-of-poverty rate"]);
    // The menu names groups first, then countries A to Z.
    const select = screen.getByLabelText(t.place);
    const groups = within(select).getByRole("group", { name: t.placeGroups });
    expect(
      within(groups)
        .getAllByRole("option")
        .map((o) => o.textContent),
    ).toEqual(["European Union", "World"]);
  });

  it("filters by years, and waits for four digits", () => {
    render(<CatalogExplorer entries={entries} />);
    type(t.fromYear, "20");
    expect(names()).toHaveLength(3); // not a year yet
    type(t.fromYear, "2023");
    expect(names()).toEqual(["Unemployment rate", "At-risk-of-poverty rate"]);
    type(t.toYear, "2024");
    expect(shown()).toBe("2 of 3 statistics");
  });

  it("warns when the years run backwards, and shows nothing", () => {
    render(<CatalogExplorer entries={entries} />);
    type(t.fromYear, "2020");
    type(t.toYear, "2010");
    expect(screen.getByRole("alert")).toHaveTextContent(t.yearsBackwards);
    expect(screen.getByLabelText(t.fromYear)).toHaveAttribute(
      "aria-invalid",
      "true",
    );
    expect(shown()).toBe("0 of 3 statistics");
  });

  it("combines every filter", () => {
    render(<CatalogExplorer entries={entries} />);
    type(t.search, "rate");
    type(t.place, "NO");
    type(t.fromYear, "2000");
    expect(names()).toEqual(["Unemployment rate", "At-risk-of-poverty rate"]);
    fireEvent.click(screen.getByRole("button", { name: /^Poverty/ }));
    expect(names()).toEqual(["At-risk-of-poverty rate"]);
  });

  it("explains an empty result and offers a way out", () => {
    render(<CatalogExplorer entries={entries} />);
    type(t.search, "zebra");
    expect(screen.getByText(t.none)).toBeInTheDocument();
    expect(screen.getByText(t.noneHint)).toBeInTheDocument();
    expect(shown()).toBe("0 of 3 statistics");
    fireEvent.click(screen.getByRole("button", { name: t.clear }));
    expect(names()).toHaveLength(3);
    expect(screen.getByLabelText(t.search)).toHaveValue("");
  });

  it("clears the year boxes too", () => {
    render(<CatalogExplorer entries={entries} />);
    type(t.fromYear, "2023");
    fireEvent.click(screen.getByRole("button", { name: t.clear }));
    expect(screen.getByLabelText(t.fromYear)).toHaveValue("");
    expect(shown()).toBe("3 statistics");
  });

  it("writes the filter to the address, and clears it again", () => {
    render(<CatalogExplorer entries={entries} />);
    type(t.search, "rent");
    type(t.place, "IT");
    expect(window.location.search).toBe("?q=rent&place=IT");
    fireEvent.click(screen.getByRole("button", { name: t.clear }));
    expect(window.location.search).toBe("");
  });

  it("opens already filtered from a link", () => {
    address = "q=rate&theme=work&place=BR&from=2000";
    render(<CatalogExplorer entries={entries} />);
    expect(screen.getByLabelText(t.search)).toHaveValue("rate");
    expect(screen.getByLabelText(t.fromYear)).toHaveValue("2000");
    expect(names()).toEqual(["Unemployment rate"]);
    // Brazil is in no entry, but the menu still shows what the link asked for.
    expect(screen.getByLabelText(t.place)).toHaveValue("BR");
  });
});
