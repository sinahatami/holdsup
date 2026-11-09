import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CheckPage } from "@/app/check/[id]/check-page";
import { generateMetadata } from "@/app/check/[id]/page";
import { readCheck } from "@/lib/api/check";
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
// The live follower is a client component with its own tests; here it only has to be chosen.
vi.mock("@/app/check/[id]/check-live", () => ({
  CheckLive: ({ id }: { id: string }) => <p>following {id} live</p>,
}));

const lookup = vi.mocked(readCheck);
const found = (view: ReturnType<typeof checkView>) =>
  lookup.mockResolvedValue({ kind: "found", view });

beforeEach(() => lookup.mockReset());

describe("CheckPage", () => {
  it("draws a finished check from what the API stored, without following it", async () => {
    found(
      checkView({
        status: "done",
        result: checkResult([holdingClaim]),
      }),
    );
    render(await CheckPage({ id: "c1" }));
    expect(
      screen.getByRole("article", { name: holdingClaim.claim.quote }),
    ).toBeInTheDocument();
    // The legend names every verdict too, so look inside the claim's own article.
    expect(
      within(screen.getByRole("article")).getByText(strings.verdicts.supported),
    ).toBeInTheDocument();
    expect(screen.queryByText(/following/)).not.toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: strings.check.back }),
    ).toBeInTheDocument();
  });

  it("shows why a failed check failed", async () => {
    found(
      checkView({
        status: "failed",
        error: {
          type: "about:blank",
          title: "At capacity",
          status: 503,
          detail: "All model providers are busy.",
        },
      }),
    );
    render(await CheckPage({ id: "c1" }));
    expect(screen.getByRole("alert")).toHaveTextContent(
      "All model providers are busy.",
    );
  });

  it.each(["queued", "running"] as const)(
    "hands a %s check to the browser to follow",
    async (status) => {
      found(checkView({ status }));
      render(await CheckPage({ id: "c1" }));
      expect(screen.getByText("following c1 live")).toBeInTheDocument();
    },
  );

  it("hands over a check the server could not read", async () => {
    lookup.mockResolvedValue({ kind: "unavailable" });
    render(await CheckPage({ id: "c9" }));
    expect(screen.getByText("following c9 live")).toBeInTheDocument();
  });

  it("is a 404 for a check that does not exist", async () => {
    lookup.mockResolvedValue({ kind: "missing" });
    await expect(CheckPage({ id: "nope" })).rejects.toThrow(/404/);
  });
});

describe("check page metadata", () => {
  const meta = (id = "c1") =>
    generateMetadata({ params: Promise.resolve({ id }) } as Parameters<
      typeof generateMetadata
    >[0]);

  it("titles a finished check by its verdict and claim, and keeps it out of search", async () => {
    found(
      checkView({
        status: "done",
        result: checkResult([partlyClaim]),
      }),
    );
    const m = await meta();
    expect(m.title).toBe(
      `Partly holds up · “${partlyClaim.claim.quote}” · HoldsUp`,
    );
    expect(m.description).toBe(partlyClaim.explanation);
    expect(m.robots).toEqual({ index: false });
    expect(m.openGraph).toMatchObject({
      siteName: "HoldsUp",
      title: `Partly holds up · “${partlyClaim.claim.quote}”`,
    });
  });

  it.each([
    [
      "a running check",
      { kind: "found", view: checkView({ status: "running" }) },
    ],
    ["an unreadable one", { kind: "unavailable" }],
    ["a missing one", { kind: "missing" }],
  ] as const)("falls back to a plain title for %s", async (_, outcome) => {
    lookup.mockResolvedValue(outcome);
    const m = await meta();
    expect(m.title).toBe(`${strings.check.heading} · ${strings.appName}`);
    expect(m.description).toBeUndefined();
    expect(m.robots).toEqual({ index: false });
  });
});
