import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CheckPage } from "@/app/(site)/check/[id]/check-page";
import { generateMetadata } from "@/app/(site)/check/[id]/page";
import { readCheck, readNewer } from "@/lib/api/check";
import { strings } from "@/lib/strings";
import {
  checkResult,
  checkView,
  holdingClaim,
  partlyClaim,
} from "@/test/fixtures";
import { EARLIER_ID, updateResult } from "@/test/watch";

vi.mock("@/lib/api/check", () => ({ readCheck: vi.fn(), readNewer: vi.fn() }));
vi.mock("next/navigation", () => ({
  notFound: () => {
    throw new Error("NEXT_HTTP_ERROR_FALLBACK;404");
  },
  useRouter: () => ({ push: vi.fn() }),
}));
// The live follower is a client component with its own tests; here it only has to be chosen.
vi.mock("@/app/(site)/check/[id]/check-live", () => ({
  CheckLive: ({ id }: { id: string }) => <p>following {id} live</p>,
}));
// The gallery read is the home page's (tested there); here it only has to be placed.
vi.mock("@/app/(site)/check/[id]/while-you-wait", () => ({
  WhileYouWait: () => <p>checks done earlier</p>,
}));

const lookup = vi.mocked(readCheck);
const found = (view: ReturnType<typeof checkView>) =>
  lookup.mockResolvedValue({ kind: "found", view });

beforeEach(() => {
  lookup.mockReset();
  vi.mocked(readNewer).mockReset();
});

describe("CheckPage and the claim watch", () => {
  const w = strings.watch;

  it("points a check whose figures were revised to the newest one, and says what it found", async () => {
    const update = updateResult();
    found(
      checkView({
        status: "done",
        result: checkResult([holdingClaim]),
        updated_by: update.id,
        watched_at: "2026-12-01T06:29:00Z",
      }),
    );
    vi.mocked(readNewer).mockResolvedValue({ id: update.id, result: update });
    render(await CheckPage({ id: "c1" }));
    expect(readNewer).toHaveBeenCalledWith(update.id);
    const note = screen.getByRole("note");
    expect(note).toHaveTextContent(w.revised);
    expect(note).toHaveTextContent(w.nowIs(strings.verdicts.partly_supported));
    expect(
      within(note).getByRole("link", { name: w.seeUpdate }),
    ).toHaveAttribute("href", `/check/${update.id}`);
    // The check itself is shown as it was, and not as recently compared: it is out of date.
    expect(
      within(screen.getByRole("article")).getByText(strings.verdicts.supported),
    ).toBeInTheDocument();
    expect(screen.queryByText(w.compared("December 1, 2026"))).toBeNull();
  });

  it("still links to the newest check when it cannot be read", async () => {
    found(
      checkView({
        status: "done",
        result: checkResult([holdingClaim]),
        updated_by: "n1",
      }),
    );
    vi.mocked(readNewer).mockResolvedValue({ id: "n1", result: null });
    render(await CheckPage({ id: "c1" }));
    expect(screen.getByRole("note")).toHaveTextContent(w.revised);
    expect(screen.getByRole("link", { name: w.seeUpdate })).toHaveAttribute(
      "href",
      "/check/n1",
    );
  });

  it("names the check an update updates, and each figure that moved", async () => {
    found(checkView({ status: "done", result: updateResult() }));
    render(await CheckPage({ id: "u1" }));
    const note = screen.getByRole("note");
    expect(note).toHaveTextContent(w.updates("November 7, 2026"));
    expect(
      within(note).getByRole("link", { name: w.seeEarlier }),
    ).toHaveAttribute("href", `/check/${EARLIER_ID}`);
    expect(
      within(note).getByText(/End value, 2023: from 7.68% to 9.18%/),
    ).toBeInTheDocument();
    expect(readNewer).not.toHaveBeenCalled();
  });

  it("says when the figures were last found unchanged", async () => {
    found(
      checkView({
        status: "done",
        result: checkResult([holdingClaim]),
        watched_at: "2026-12-01T06:29:00Z",
      }),
    );
    render(await CheckPage({ id: "c1" }));
    expect(
      screen.getByText(w.compared("December 1, 2026")),
    ).toBeInTheDocument();
    expect(screen.queryByRole("note")).toBeNull();
  });
});

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
    // A failure that trying again can fix offers to send the same text again.
    expect(
      screen.getByRole("button", { name: strings.problem.retry }),
    ).toBeInTheDocument();
    // Earlier checks are for a reader waiting on busy providers, not for any failure.
    expect(screen.queryByText("checks done earlier")).not.toBeInTheDocument();
  });

  it("at capacity, shows when HoldsUp is back and the checks done earlier", async () => {
    found(
      checkView({
        status: "failed",
        error: {
          type: "/problems/at-capacity",
          title: "At capacity",
          status: 503,
          detail: "Every free model provider is busy or out of quota.",
          retry_after: 1800,
        },
      }),
    );
    render(await CheckPage({ id: "c1" }));
    const t = strings.problem;
    expect(screen.getByRole("alert")).toHaveTextContent(
      t.capacity.backIn("about 30 minutes"),
    );
    expect(
      screen.getByRole("button", { name: t.retryIn("30 min") }),
    ).toBeDisabled();
    expect(await screen.findByText("checks done earlier")).toBeInTheDocument();
  });

  it("offers no retry for a text the API refused as it is", async () => {
    found(
      checkView({
        status: "failed",
        error: { type: "about:blank", title: "Unprocessable", status: 422 },
      }),
    );
    render(await CheckPage({ id: "c1" }));
    expect(
      screen.queryByRole("button", { name: strings.problem.retry }),
    ).not.toBeInTheDocument();
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
    expect(m.twitter).toMatchObject({ card: "summary_large_image" });
    expect(m.openGraph).toMatchObject({
      siteName: "HoldsUp",
      title: `Partly holds up · “${partlyClaim.claim.quote}”`,
    });
  });

  it("points chat and social apps at the check's own picture, whatever its state", async () => {
    const image = {
      url: "/check/c1/opengraph-image",
      width: 1200,
      height: 630,
      alt: strings.og.alt,
    };
    found(checkView({ status: "done", result: checkResult([partlyClaim]) }));
    const done = await meta();
    expect(done.openGraph?.images).toEqual([image]);
    expect(done.twitter?.images).toEqual([image]);
    lookup.mockResolvedValue({ kind: "missing" });
    const missing = await meta();
    expect(missing.openGraph?.images).toEqual([image]);
    expect(missing.twitter).toMatchObject({ card: "summary_large_image" });
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
