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
const URL_ = () => `${location.origin}/check/abc-123`;

const writeText = vi.fn();

function open() {
  return render(
    <ShareActions title="Holds up · “Debt is 133% of GDP.”" text={TEXT} />,
  );
}

function full() {
  return render(
    <ShareActions
      title="Holds up · “Debt is 133% of GDP.”"
      text={TEXT}
      image={{ href: "/check/c1/opengraph-image", name: "holdsup-c1.png" }}
      embed={{ id: "abc-123", claims: 1 }}
    />,
  );
}

const tab = (name: string) => screen.getByRole("tab", { name });
const preview = () => screen.getByTestId("share-preview");
const more = () => screen.getByRole("button", { name: t.more });

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
  it("is a labelled region: one row with the link, and the other ways closed", () => {
    full();
    expect(screen.getByRole("region", { name: t.heading })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: t.copyLink }),
    ).toBeInTheDocument();
    expect(more()).toHaveAttribute("aria-expanded", "false");
    // Closed, the tabs are out of the page for everyone.
    expect(screen.queryByRole("tablist")).toBeNull();
    expect(screen.queryByTestId("share-preview")).not.toBeVisible();
  });

  it("opens the other ways as tabs, the summary first, and closes them again", () => {
    full();
    fireEvent.click(more());
    expect(more()).toHaveAttribute("aria-expanded", "true");
    const panel = document.getElementById(
      more().getAttribute("aria-controls")!,
    );
    expect(panel).toBeVisible();
    expect(screen.getByRole("tablist", { name: t.more })).toBeInTheDocument();
    expect(screen.getAllByRole("tab").map((el) => el.textContent)).toEqual([
      t.tabs.summary,
      t.tabs.embed,
      t.tabs.image,
    ]);
    expect(tab(t.tabs.summary)).toHaveAttribute("aria-selected", "true");
    // One tab stop for the whole list; arrows move within it.
    expect(tab(t.tabs.summary)).toHaveAttribute("tabindex", "0");
    expect(tab(t.tabs.embed)).toHaveAttribute("tabindex", "-1");
    expect(screen.getByRole("tabpanel")).toHaveAccessibleName(t.tabs.summary);
    fireEvent.click(more());
    expect(more()).toHaveAttribute("aria-expanded", "false");
    expect(panel).not.toBeVisible();
  });

  it("offers only the ways this check has", () => {
    open();
    fireEvent.click(more());
    expect(screen.getAllByRole("tab")).toHaveLength(1);
    expect(screen.queryByRole("tab", { name: t.tabs.embed })).toBeNull();
    expect(screen.queryByRole("tab", { name: t.tabs.image })).toBeNull();
  });

  it("copies the link without the page's query or fragment, ticks the button and says who can open it", async () => {
    open();
    fireEvent.click(screen.getByRole("button", { name: t.copyLink }));
    await waitFor(() => expect(writeText).toHaveBeenCalledWith(URL_()));
    expect(await screen.findByRole("status")).toHaveTextContent(t.linkCopied);
    // The button keeps its name (what it does), so it can be pressed again.
    expect(
      screen.getByRole("button", { name: t.copyLink }),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("share-link")).toBeNull();
  });

  it("shows and copies a summary with the claim, the verdict and the link", async () => {
    open();
    fireEvent.click(more());
    expect(preview().textContent).toBe(`${TEXT}\n${URL_()}`);
    expect(screen.getByText(t.hints.summary)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: t.copySummary }));
    await waitFor(() => expect(writeText).toHaveBeenCalled());
    const copied = writeText.mock.calls[0][0] as string;
    expect(copied).toBe(preview().textContent);
    expect(await screen.findByRole("status")).toHaveTextContent(
      t.summaryCopied,
    );
  });

  it("shows and copies the iframe code for this site", async () => {
    full();
    fireEvent.click(more());
    fireEvent.click(tab(t.tabs.embed));
    expect(preview().textContent).toMatch(/^<iframe /);
    fireEvent.click(screen.getByRole("button", { name: t.embed }));
    await waitFor(() => expect(writeText).toHaveBeenCalledOnce());
    const code = writeText.mock.calls[0][0] as string;
    expect(code).toBe(preview().textContent);
    expect(code).toContain(`src="${location.origin}/embed/abc-123"`);
    expect(code).toContain("Debt is 133% of GDP.");
    expect(await screen.findByRole("status")).toHaveTextContent(t.embedCopied);
  });

  it("shows the card image and offers it to download", () => {
    full();
    fireEvent.click(more());
    fireEvent.click(tab(t.tabs.image));
    expect(screen.getByRole("img", { name: strings.og.alt })).toHaveAttribute(
      "src",
      "/check/c1/opengraph-image",
    );
    const link = screen.getByRole("link", { name: t.image });
    expect(link).toHaveAttribute("href", "/check/c1/opengraph-image");
    expect(link).toHaveAttribute("download", "holdsup-c1.png");
  });

  it("moves between tabs with the arrow keys, Home and End, and wraps around", () => {
    full();
    fireEvent.click(more());
    const list = screen.getByRole("tablist");
    fireEvent.keyDown(list, { key: "ArrowRight" });
    expect(tab(t.tabs.embed)).toHaveFocus();
    expect(tab(t.tabs.embed)).toHaveAttribute("aria-selected", "true");
    fireEvent.keyDown(list, { key: "End" });
    expect(tab(t.tabs.image)).toHaveFocus();
    fireEvent.keyDown(list, { key: "ArrowRight" });
    expect(tab(t.tabs.summary)).toHaveFocus();
    fireEvent.keyDown(list, { key: "ArrowLeft" });
    expect(tab(t.tabs.image)).toHaveFocus();
    fireEvent.keyDown(list, { key: "Home" });
    expect(tab(t.tabs.summary)).toHaveFocus();
  });

  it("clears the last status when another tab is chosen or the ways are closed", async () => {
    full();
    fireEvent.click(screen.getByRole("button", { name: t.copyLink }));
    expect(await screen.findByRole("status")).toHaveTextContent(t.linkCopied);
    fireEvent.click(more());
    expect(screen.getByRole("status")).toBeEmptyDOMElement();
    fireEvent.click(screen.getByRole("button", { name: t.copySummary }));
    expect(await screen.findByRole("status")).toHaveTextContent(
      t.summaryCopied,
    );
    fireEvent.click(tab(t.tabs.embed));
    expect(screen.getByRole("status")).toBeEmptyDOMElement();
  });

  it("shows the link, selected, so it can be copied by hand when copying it fails", async () => {
    writeText.mockRejectedValue(new Error("denied"));
    open();
    expect(screen.queryByTestId("share-link")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: t.copyLink }));
    expect(await screen.findByRole("status")).toHaveTextContent(t.failed);
    expect(screen.getByTestId("share-link")).toHaveTextContent(URL_());
    expect(window.getSelection()?.toString()).toBe(URL_());
    // Once a copy works, the link goes away again.
    writeText.mockResolvedValue(undefined);
    fireEvent.click(screen.getByRole("button", { name: t.copyLink }));
    expect(await screen.findByText(t.linkCopied)).toBeInTheDocument();
    expect(screen.queryByTestId("share-link")).toBeNull();
  });

  it("selects the preview so it can be copied by hand when copying a summary fails", async () => {
    writeText.mockRejectedValue(new Error("denied"));
    open();
    fireEvent.click(more());
    fireEvent.click(screen.getByRole("button", { name: t.copySummary }));
    expect(await screen.findByRole("status")).toHaveTextContent(t.failed);
    expect(window.getSelection()?.toString()).toBe(preview().textContent);
  });

  it("clears the status after a few seconds", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    open();
    fireEvent.click(screen.getByRole("button", { name: t.copyLink }));
    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent(t.linkCopied),
    );
    act(() => {
      vi.advanceTimersByTime(4500);
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
      url: URL_(),
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
});
