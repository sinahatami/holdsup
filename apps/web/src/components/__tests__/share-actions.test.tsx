import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ShareActions } from "@/components/molecules/share-actions";
import { strings } from "@/lib/strings";

const t = strings.share;
const TEXT =
  "“Debt is 133% of GDP.”\nHolds up. Checked with HoldsUp, against Eurostat.";

const writeText = vi.fn();

function open() {
  return render(
    <ShareActions title="Holds up · “Debt is 133% of GDP.”" text={TEXT} />,
  );
}

beforeEach(() => {
  writeText.mockReset().mockResolvedValue(undefined);
  vi.stubGlobal("navigator", { ...navigator, clipboard: { writeText } });
  window.history.pushState({}, "", "/check/abc-123?x=1#top");
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("ShareActions", () => {
  it("offers the check's card image to download, only when there is one", () => {
    const { unmount } = render(
      <ShareActions
        title="Holds up"
        text={TEXT}
        image={{ href: "/check/c1/opengraph-image", name: "holdsup-c1.png" }}
      />,
    );
    const link = screen.getByRole("link", { name: t.image });
    expect(link).toHaveAttribute("href", "/check/c1/opengraph-image");
    expect(link).toHaveAttribute("download", "holdsup-c1.png");
    unmount();
    open();
    expect(screen.queryByRole("link", { name: t.image })).toBeNull();
  });

  it("copies the link of this page, without its query or fragment", async () => {
    open();
    fireEvent.click(screen.getByRole("button", { name: t.copyLink }));
    await waitFor(() =>
      expect(writeText).toHaveBeenCalledWith(
        `${location.origin}/check/abc-123`,
      ),
    );
    expect(await screen.findByRole("status")).toHaveTextContent(t.linkCopied);
  });

  it("copies a summary with the claim, the verdict and the link", async () => {
    open();
    fireEvent.click(screen.getByRole("button", { name: t.copySummary }));
    await waitFor(() => expect(writeText).toHaveBeenCalled());
    const copied = writeText.mock.calls[0][0] as string;
    expect(copied).toContain("“Debt is 133% of GDP.”");
    expect(copied).toContain("Holds up");
    expect(copied.endsWith(`${location.origin}/check/abc-123`)).toBe(true);
    expect(await screen.findByRole("status")).toHaveTextContent(
      t.summaryCopied,
    );
  });

  it("says so when it could not copy", async () => {
    writeText.mockRejectedValue(new Error("denied"));
    open();
    fireEvent.click(screen.getByRole("button", { name: t.copyLink }));
    expect(await screen.findByRole("status")).toHaveTextContent(t.failed);
  });

  it("clears the status after a few seconds", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    open();
    fireEvent.click(screen.getByRole("button", { name: t.copyLink }));
    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent(t.linkCopied),
    );
    act(() => {
      vi.advanceTimersByTime(3500);
    });
    expect(screen.getByRole("status")).toBeEmptyDOMElement();
  });

  it("offers the share sheet only where the browser has one", () => {
    const { unmount } = open();
    expect(
      screen.queryByRole("button", { name: t.native }),
    ).not.toBeInTheDocument();
    unmount();
    vi.stubGlobal("navigator", {
      ...navigator,
      clipboard: { writeText },
      share: vi.fn(),
    });
    open();
    expect(screen.getByRole("button", { name: t.native })).toBeInTheDocument();
  });

  it("shares the title, the text and the link", async () => {
    const share = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal("navigator", {
      ...navigator,
      clipboard: { writeText },
      share,
    });
    open();
    fireEvent.click(screen.getByRole("button", { name: t.native }));
    await waitFor(() => expect(share).toHaveBeenCalled());
    expect(share).toHaveBeenCalledWith({
      title: "Holds up · “Debt is 133% of GDP.”",
      text: TEXT,
      url: `${location.origin}/check/abc-123`,
    });
  });

  it("does not call it a failure when the share sheet is closed", async () => {
    const share = vi
      .fn()
      .mockRejectedValue(new DOMException("closed", "AbortError"));
    vi.stubGlobal("navigator", {
      ...navigator,
      clipboard: { writeText },
      share,
    });
    open();
    fireEvent.click(screen.getByRole("button", { name: t.native }));
    await waitFor(() => expect(share).toHaveBeenCalled());
    expect(screen.getByRole("status")).toBeEmptyDOMElement();
  });

  it("does say so when sharing fails for another reason", async () => {
    const share = vi
      .fn()
      .mockRejectedValue(new DOMException("no", "NotAllowedError"));
    vi.stubGlobal("navigator", {
      ...navigator,
      clipboard: { writeText },
      share,
    });
    open();
    fireEvent.click(screen.getByRole("button", { name: t.native }));
    expect(await screen.findByRole("status")).toHaveTextContent(t.failed);
  });

  it("is a labelled region whose buttons can be reached by keyboard", () => {
    open();
    expect(screen.getByRole("region", { name: t.heading })).toBeInTheDocument();
    for (const name of [t.copyLink, t.copySummary]) {
      expect(screen.getByRole("button", { name })).not.toHaveAttribute(
        "tabindex",
        "-1",
      );
    }
  });
});
