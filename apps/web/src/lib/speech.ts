import { strings } from "@/lib/strings";

/**
 * The few parts of the browser's speech recognition that HoldsUp uses. TypeScript's own DOM
 * types leave it out because browsers still ship it under a `webkit` name.
 */
export interface SpeechResultLike {
  readonly 0: { readonly transcript: string };
  readonly length: number;
  readonly isFinal: boolean;
}

export interface SpeechRecognitionLike {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult:
    ((e: { readonly results: ArrayLike<SpeechResultLike> }) => void) | null;
  onerror: ((e: { readonly error: string }) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}

export type SpeechRecognitionCtor = new () => SpeechRecognitionLike;

type SpeechWindow = Window & {
  SpeechRecognition?: SpeechRecognitionCtor;
  webkitSpeechRecognition?: SpeechRecognitionCtor;
};

/** The browser's speech recognition, or null where it has none (Firefox, for one). */
export function recognitionCtor(
  win: SpeechWindow | undefined = typeof window === "undefined"
    ? undefined
    : window,
): SpeechRecognitionCtor | null {
  return win?.SpeechRecognition ?? win?.webkitSpeechRecognition ?? null;
}

/** Everything heard so far in one go, finished words and the ones still being guessed. */
export function transcriptOf(results: ArrayLike<SpeechResultLike>): string {
  return Array.from(results, (r) => r[0].transcript).join("");
}

/** What the box should say: what was typed before, then what was spoken, one space apart. */
export function withSpoken(base: string, spoken: string): string {
  return [base.trimEnd(), spoken.trim()].filter(Boolean).join(" ");
}

/** The language to listen for: the visitor's own when HoldsUp offers it, English otherwise. */
export function defaultSpeechLanguage(
  browserLanguage: string | undefined,
): string {
  const languages = strings.voice.languages;
  const own = browserLanguage?.toLowerCase().split("-")[0];
  return (
    languages.find((l) => l.code.toLowerCase().split("-")[0] === own) ??
    languages[0]
  ).code;
}

export type SpeechProblem = keyof typeof strings.voice.problems;

/** What went wrong, from the browser's error code; null for "aborted", which is not a failure. */
export function speechProblem(code: string): SpeechProblem | null {
  switch (code) {
    case "aborted":
      return null;
    case "not-allowed":
    case "service-not-allowed":
      return "denied";
    case "no-speech":
      return "silent";
    case "audio-capture":
      return "noMic";
    case "network":
      return "offline";
    default:
      return "other";
  }
}
