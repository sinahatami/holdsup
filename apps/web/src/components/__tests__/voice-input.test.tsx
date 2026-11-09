import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CheckForm } from "@/components/organisms/check-form";
import type { SpeechRecognitionLike } from "@/lib/speech";
import { strings } from "@/lib/strings";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

const t = strings.voice;

/** A stand-in for the browser's recognition that the test drives by hand. */
class FakeRecognition implements SpeechRecognitionLike {
  static all: FakeRecognition[] = [];
  lang = "";
  continuous = true;
  interimResults = false;
  onresult: SpeechRecognitionLike["onresult"] = null;
  onerror: SpeechRecognitionLike["onerror"] = null;
  onend: SpeechRecognitionLike["onend"] = null;
  started = false;
  aborted = false;
  constructor() {
    FakeRecognition.all.push(this);
  }
  start() {
    this.started = true;
  }
  stop() {
    this.onend?.();
  }
  abort() {
    this.aborted = true;
    this.onend?.();
  }
  /** What was heard so far, as the browser reports it. */
  hear(...parts: string[]) {
    const results = parts.map((transcript) => ({
      0: { transcript },
      length: 1,
      isFinal: false,
    }));
    this.onresult?.({ results });
  }
  fail(error: string) {
    this.onerror?.({ error });
    this.onend?.();
  }
}

const latest = () => FakeRecognition.all.at(-1)!;
const box = () => screen.getByRole("textbox") as HTMLTextAreaElement;
const speak = () => screen.getByRole("button", { name: t.start });
const stop = () => screen.getByRole("button", { name: t.stop });
const status = () => screen.getByRole("status");

beforeEach(() => {
  FakeRecognition.all = [];
  push.mockReset();
  vi.stubGlobal("SpeechRecognition", FakeRecognition);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  delete (window as { SpeechRecognition?: unknown }).SpeechRecognition;
});

describe("voice input in the claim box", () => {
  it("is not offered in a browser that cannot listen", () => {
    delete (window as { SpeechRecognition?: unknown }).SpeechRecognition;
    render(<CheckForm />);
    expect(
      screen.queryByRole("button", { name: t.start }),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("listens for one utterance, with guesses on, and says so", () => {
    render(<CheckForm />);
    expect(status()).toBeEmptyDOMElement();
    fireEvent.click(speak());
    expect(latest().started).toBe(true);
    expect(latest().continuous).toBe(false);
    expect(latest().interimResults).toBe(true);
    expect(latest().lang).toBe("en-US");
    expect(stop()).toBeInTheDocument();
    expect(status()).toHaveTextContent(t.listening);
    // The audio is heard by the browser's own service, and the page says it.
    expect(status()).toHaveTextContent("may send the audio to its provider");
  });

  it("writes what is heard into the box as it comes, replacing the guesses", () => {
    render(<CheckForm />);
    fireEvent.click(speak());
    act(() => latest().hear("Italy's debt"));
    expect(box().value).toBe("Italy's debt");
    act(() => latest().hear("Italy's debt", " is 133% of GDP"));
    expect(box().value).toBe("Italy's debt is 133% of GDP");
  });

  it("adds to what was typed, and asks to check the figures once it stops", () => {
    render(<CheckForm />);
    fireEvent.change(box(), { target: { value: "Italy:" } });
    fireEvent.click(speak());
    act(() => latest().hear("debt is 133%"));
    expect(box().value).toBe("Italy: debt is 133%");
    act(() => latest().stop());
    expect(speak()).toBeInTheDocument();
    expect(status()).toHaveTextContent(t.review(strings.home.submit));
  });

  it("never submits by itself", () => {
    render(<CheckForm />);
    fireEvent.click(speak());
    act(() => latest().hear("Italy's debt is 133% of GDP"));
    act(() => latest().stop());
    expect(push).not.toHaveBeenCalled();
    expect(
      screen.getByRole("button", { name: strings.home.submit }),
    ).toBeEnabled();
  });

  it("stops when asked, keeping what was heard", () => {
    render(<CheckForm />);
    fireEvent.click(speak());
    act(() => latest().hear("rents rose"));
    fireEvent.click(stop());
    expect(box().value).toBe("rents rose");
    expect(speak()).toBeInTheDocument();
  });

  it("gives way to typing: late words do not overwrite it", () => {
    render(<CheckForm />);
    fireEvent.click(speak());
    act(() => latest().hear("rents rose"));
    const rec = latest();
    fireEvent.change(box(), { target: { value: "rents fell" } });
    expect(rec.aborted).toBe(true);
    expect(speak()).toBeInTheDocument();
    act(() => rec.hear("rents rose by 5%"));
    expect(box().value).toBe("rents fell");
  });

  it("starts a fresh listen each time, adding to the box", () => {
    render(<CheckForm />);
    fireEvent.click(speak());
    act(() => latest().hear("Italy's debt"));
    act(() => latest().stop());
    fireEvent.click(speak());
    act(() => latest().hear("is 133% of GDP"));
    expect(FakeRecognition.all).toHaveLength(2);
    expect(box().value).toBe("Italy's debt is 133% of GDP");
  });

  it.each([
    ["not-allowed", t.problems.denied],
    ["no-speech", t.problems.silent],
    ["audio-capture", t.problems.noMic],
    ["network", t.problems.offline],
    ["language-not-supported", t.problems.other],
  ])("explains %s, and goes back to ready", (code, message) => {
    render(<CheckForm />);
    fireEvent.click(speak());
    act(() => latest().fail(code));
    expect(screen.getByRole("alert")).toHaveTextContent(message);
    expect(speak()).toBeInTheDocument();
    expect(status()).toBeEmptyDOMElement();
  });

  it("says nothing when the listen was simply aborted", () => {
    render(<CheckForm />);
    fireEvent.click(speak());
    act(() => latest().fail("aborted"));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("clears the problem on the next try", () => {
    render(<CheckForm />);
    fireEvent.click(speak());
    act(() => latest().fail("no-speech"));
    fireEvent.click(speak());
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("does not claim the figures were heard when nothing was", () => {
    render(<CheckForm />);
    fireEvent.click(speak());
    act(() => latest().fail("no-speech"));
    expect(status()).toBeEmptyDOMElement();
  });

  it("listens in the visitor's language when it is offered, and the menu can change it", () => {
    vi.spyOn(navigator, "language", "get").mockReturnValue("it-IT");
    render(<CheckForm />);
    const menu = screen.getByRole("combobox", { name: t.language });
    expect(menu).toHaveValue("it-IT");
    fireEvent.change(menu, { target: { value: "en-US" } });
    fireEvent.click(speak());
    expect(latest().lang).toBe("en-US");
    // It cannot change in the middle of a listen.
    expect(menu).toBeDisabled();
  });

  it("stops listening when the component goes away", () => {
    const { unmount } = render(<CheckForm />);
    fireEvent.click(speak());
    const rec = latest();
    unmount();
    expect(rec.aborted).toBe(true);
  });

  it("does not start twice when pressed again before it has stopped", () => {
    render(<CheckForm />);
    fireEvent.click(speak());
    fireEvent.click(stop());
    expect(FakeRecognition.all).toHaveLength(1);
  });
});
