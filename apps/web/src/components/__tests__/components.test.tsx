import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CheckForm } from "@/components/check-form";
import { Gallery } from "@/components/gallery";
import { Receipt } from "@/components/receipt";
import { Trace } from "@/components/trace";
import { VerdictBadge } from "@/components/verdict";
import type { ClaimResult } from "@/lib/api/client";
import { strings } from "@/lib/strings";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

describe("VerdictBadge", () => {
  it.each(Object.keys(strings.verdicts) as (keyof typeof strings.verdicts)[])(
    "names the %s verdict in words",
    (label) => {
      render(<VerdictBadge label={label} />);
      expect(screen.getByText(strings.verdicts[label])).toBeInTheDocument();
    },
  );
});

describe("Trace", () => {
  it("lists steps with a text state", () => {
    render(
      <Trace
        rows={[
          {
            key: "all:extract",
            step: "extract",
            claim: null,
            state: "ok",
            summary: "1 claim",
            models: [],
            ms: 3,
          },
          {
            key: "0:match",
            step: "match",
            claim: 0,
            state: "running",
            summary: "",
            models: [],
            ms: null,
          },
        ]}
      />,
    );
    expect(screen.getByText(/done/)).toBeInTheDocument();
    expect(screen.getByText(/running/)).toBeInTheDocument();
  });
  it("renders nothing without rows", () => {
    const { container } = render(<Trace rows={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("Gallery", () => {
  it("links each item to its check", () => {
    render(
      <Gallery
        items={[
          {
            id: "abc",
            text: "A claim",
            created_at: "",
            verdicts: ["supported"],
            indicators: [],
          },
        ]}
      />,
    );
    expect(screen.getByRole("link", { name: "A claim" })).toHaveAttribute(
      "href",
      "/check/abc",
    );
  });
});

const claim = {
  index: 0,
  indicator: {
    id: "i",
    name: "Unemployment rate",
    source: "eurostat",
    source_code: "x",
    unit: "%",
    frequency: "A",
    definition: "Share unemployed",
  },
  data: {
    source: "Eurostat",
    dataset: "une_rt_a",
    url: "https://e.u",
    retrieved_at: "2026-11-07",
    raw_sha256: "ab12",
    label: "",
    places: [],
    rows: 2,
  },
  operations: [
    {
      op: "change",
      args: { start: "2015", end: "2023" },
      inputs: [{ geo: "IT", period: "2015", value: 11.9 }],
      value: -4.2,
      extras: {},
      series: null,
      unit: "pp",
      flags: [],
    },
  ],
  models: [{ step: "extract", provider: "groq", model: "m" }],
} as unknown as ClaimResult;

describe("Receipt", () => {
  it("shows source, fingerprint, operations and versions", () => {
    render(
      <Receipt
        claim={claim}
        versions={{ app: "0.1.0", catalog: "0.2.0", tolerances: 1 }}
      />,
    );
    expect(screen.getByText("Unemployment rate")).toBeInTheDocument();
    expect(screen.getByText("ab12")).toBeInTheDocument();
    expect(screen.getByText(/change\(/)).toBeInTheDocument();
    expect(screen.getByText(/catalog 0.2.0/)).toBeInTheDocument();
  });
  it("says so when no data was fetched", () => {
    render(
      <Receipt
        claim={{
          ...claim,
          data: null,
          indicator: null,
          operations: [],
          models: [],
        }}
        versions={{ app: "a", catalog: "c", tolerances: 1 }}
      />,
    );
    expect(screen.getByText(strings.receipt.noData)).toBeInTheDocument();
  });
});

describe("CheckForm", () => {
  it("fills the box from an example and posts it", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: true, json: async () => ({ id: "new-id" }) });
    vi.stubGlobal("fetch", fetchMock);
    render(<CheckForm />);
    fireEvent.click(
      screen.getByRole("button", { name: strings.home.examples[0] }),
    );
    fireEvent.click(screen.getByRole("button", { name: strings.home.submit }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/check/new-id"));
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      text: strings.home.examples[0],
    });
    vi.unstubAllGlobals();
  });

  it("shows the problem detail when the API refuses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 429,
        statusText: "x",
        json: async () => ({
          title: "Too many",
          status: 429,
          detail: "Slow down.",
        }),
      }),
    );
    render(<CheckForm />);
    fireEvent.change(screen.getByLabelText(strings.home.inputLabel), {
      target: { value: "claim" },
    });
    fireEvent.click(screen.getByRole("button", { name: strings.home.submit }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Slow down.");
    vi.unstubAllGlobals();
  });

  it("blocks text over the limit", () => {
    render(<CheckForm />);
    fireEvent.change(screen.getByLabelText(strings.home.inputLabel), {
      target: { value: "x".repeat(2001) },
    });
    expect(
      screen.getByRole("button", { name: strings.home.submit }),
    ).toBeDisabled();
    expect(screen.getByRole("alert")).toHaveTextContent(strings.home.tooLong);
  });
});
