import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { EmbedPage } from "@/app/embed/[id]/embed-page";
import EmbedNotFound from "@/app/embed/[id]/not-found";
import { generateMetadata } from "@/app/embed/[id]/page";
import { readCheck } from "@/lib/api/check";
import { headlineFigure } from "@/lib/receipt";
import { strings } from "@/lib/strings";
import {
  checkResult,
  checkView,
  holdingClaim,
  partlyClaim,
} from "@/test/fixtures";

vi.mock("@/lib/api/check", () => ({ readCheck: vi.fn() }));
vi.mock("next/navigation", () => ({
  notFound: () => {
    throw new Error("NEXT_HTTP_ERROR_FALLBACK;404");
  },
}));

const t = strings.embed;
const lookup = vi.mocked(readCheck);
const found = (view: ReturnType<typeof checkView>) =>
  lookup.mockResolvedValue({ kind: "found", view });

beforeEach(() => lookup.mockReset());

/** The link out of the frame: it must open HoldsUp in a new tab, not inside the frame. */
function linkOut(name: string | RegExp) {
  const link = screen.getByRole("link", { name });
  expect(link).toHaveAttribute("target", "_blank");
  expect(link).toHaveAttribute("rel", expect.stringContaining("noopener"));
  return link;
}

describe("EmbedPage", () => {
  it("shows one claim's stamp, words and figures, and links to its receipt", async () => {
    found(checkView({ status: "done", result: checkResult([holdingClaim]) }));
    render(await EmbedPage({ id: "c1" }));
    expect(
      screen.getByRole("heading", { level: 1, name: strings.appName }),
    ).toBeInTheDocument();
    const claim = screen.getByRole("article", {
      name: holdingClaim.claim.quote,
    });
    expect(within(claim).getByText(strings.verdicts.supported)).toBeVisible();
    const head = headlineFigure(holdingClaim);
    if (!head) throw new Error("the fixture states a figure");
    expect(within(claim).getByText(head.claimed)).toBeInTheDocument();
    expect(within(claim).getByText(head.official)).toBeInTheDocument();
    expect(linkOut(new RegExp(t.fullReceipt))).toHaveAttribute(
      "href",
      "/check/c1",
    );
    // An embed is the verdict alone: no site navigation, no share buttons.
    expect(screen.queryByRole("navigation")).toBeNull();
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("counts how many of several claims hold up and gives each its own stamp", async () => {
    found(
      checkView({
        status: "done",
        result: checkResult([holdingClaim, { ...partlyClaim, index: 1 }]),
      }),
    );
    render(await EmbedPage({ id: "c1" }));
    expect(screen.getByText(strings.home.card.summary(1, 2))).toBeVisible();
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(
      within(items[0]).getByText(strings.verdicts.supported),
    ).toBeInTheDocument();
    expect(
      within(items[1]).getByText(strings.verdicts.partly_supported),
    ).toBeInTheDocument();
  });

  it.each([
    ["running", checkView({ status: "running" }), t.running],
    ["queued", checkView({ status: "queued" }), t.running],
    [
      "failed",
      checkView({
        status: "failed",
        error: { type: "about:blank", title: "Failed", status: 500 },
      }),
      t.failed,
    ],
    [
      "empty",
      checkView({ status: "done", result: checkResult([]) }),
      t.noClaims,
    ],
  ])(
    "says why a %s check has no verdict and links to its page",
    async (_, view, text) => {
      found(view);
      render(await EmbedPage({ id: "c1" }));
      expect(screen.getByText(text)).toBeInTheDocument();
      expect(linkOut(new RegExp(t.openCheck))).toHaveAttribute(
        "href",
        "/check/c1",
      );
    },
  );

  it("says when the API could not be read", async () => {
    lookup.mockResolvedValue({ kind: "unavailable" });
    render(await EmbedPage({ id: "c1" }));
    expect(screen.getByText(t.unavailable)).toBeInTheDocument();
  });

  it("is not found when no check has that id", async () => {
    lookup.mockResolvedValue({ kind: "missing" });
    await expect(EmbedPage({ id: "nope" })).rejects.toThrow("404");
  });
});

describe("EmbedNotFound", () => {
  it("says so in the frame and links to HoldsUp in a new tab", () => {
    render(<EmbedNotFound />);
    expect(screen.getByText(t.missing)).toBeInTheDocument();
    expect(linkOut(new RegExp(t.openHoldsUp))).toHaveAttribute("href", "/");
  });
});

describe("generateMetadata", () => {
  const params = (id: string) =>
    ({ params: Promise.resolve({ id }) }) as Parameters<
      typeof generateMetadata
    >[0];

  it("titles a finished check by its verdict and keeps it out of search", async () => {
    found(checkView({ status: "done", result: checkResult([holdingClaim]) }));
    const meta = await generateMetadata(params("c1"));
    expect(meta.title).toContain(strings.verdicts.supported);
    expect(meta.robots).toEqual({ index: false });
  });

  it("has a plain title while there is no verdict", async () => {
    lookup.mockResolvedValue({ kind: "unavailable" });
    const meta = await generateMetadata(params("c1"));
    expect(meta.title).toBe(`${t.pageTitle} · ${strings.appName}`);
    expect(meta.robots).toEqual({ index: false });
  });
});
