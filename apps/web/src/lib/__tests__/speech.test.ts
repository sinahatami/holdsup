import { describe, expect, it } from "vitest";
import {
  defaultSpeechLanguage,
  recognitionCtor,
  speechProblem,
  transcriptOf,
  withSpoken,
  type SpeechRecognitionCtor,
} from "@/lib/speech";

const result = (transcript: string, isFinal = true) => ({
  0: { transcript },
  length: 1,
  isFinal,
});

describe("recognitionCtor", () => {
  const Fake = class {} as unknown as SpeechRecognitionCtor;
  const win = (extra: object) => extra as Window;

  it("finds the standard name, then the webkit one", () => {
    expect(recognitionCtor(win({ SpeechRecognition: Fake }))).toBe(Fake);
    expect(recognitionCtor(win({ webkitSpeechRecognition: Fake }))).toBe(Fake);
  });

  it("is null in a browser that cannot listen, and with no window", () => {
    expect(recognitionCtor(win({}))).toBeNull();
    expect(recognitionCtor(undefined)).toBeNull();
  });
});

describe("transcriptOf", () => {
  it("joins what was heard, finished and still guessed", () => {
    expect(
      transcriptOf([result("Italy's debt"), result(" is 133%", false)]),
    ).toBe("Italy's debt is 133%");
  });
});

describe("withSpoken", () => {
  it("puts the speech after what was typed, one space apart", () => {
    expect(withSpoken("Italy:  \n", " debt is 133% ")).toBe(
      "Italy: debt is 133%",
    );
  });

  it("is just the speech when the box was empty, and just the text when nothing was said", () => {
    expect(withSpoken("", "debt is 133%")).toBe("debt is 133%");
    expect(withSpoken("Italy", "")).toBe("Italy");
  });
});

describe("defaultSpeechLanguage", () => {
  it("listens in the visitor's language when HoldsUp offers it", () => {
    expect(defaultSpeechLanguage("it")).toBe("it-IT");
    expect(defaultSpeechLanguage("it-CH")).toBe("it-IT");
    expect(defaultSpeechLanguage("IT-it")).toBe("it-IT");
  });

  it("falls back to English", () => {
    expect(defaultSpeechLanguage("fa-IR")).toBe("en-US");
    expect(defaultSpeechLanguage("en-GB")).toBe("en-US");
    expect(defaultSpeechLanguage(undefined)).toBe("en-US");
  });
});

describe("speechProblem", () => {
  it.each([
    ["not-allowed", "denied"],
    ["service-not-allowed", "denied"],
    ["no-speech", "silent"],
    ["audio-capture", "noMic"],
    ["network", "offline"],
    ["language-not-supported", "other"],
  ])("reads %s as %s", (code, problem) => {
    expect(speechProblem(code)).toBe(problem);
  });

  it("does not count aborting as a failure", () => {
    expect(speechProblem("aborted")).toBeNull();
  });
});
