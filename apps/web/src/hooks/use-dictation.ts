"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import {
  recognitionCtor,
  speechProblem,
  transcriptOf,
  type SpeechProblem,
  type SpeechRecognitionLike,
} from "@/lib/speech";

const noop = () => () => {};

/**
 * Speech to text with the browser's own recognition, so nothing is installed and HoldsUp never
 * receives audio. One utterance at a time: it stops after a pause, and speaking again adds more.
 * `onText` gets everything heard in this go so far, finished words and guesses, as it changes.
 * `supported` is false on the server and before hydration, then true where the browser can listen.
 */
export function useDictation({
  lang,
  onText,
}: {
  lang: string;
  onText: (spoken: string) => void;
}) {
  const supported = useSyncExternalStore(
    noop,
    () => recognitionCtor() !== null,
    () => false,
  );
  const [listening, setListening] = useState(false);
  const [heard, setHeard] = useState(false);
  const [problem, setProblem] = useState<SpeechProblem | null>(null);
  const current = useRef<SpeechRecognitionLike | null>(null);
  const latestOnText = useRef(onText);

  useEffect(() => {
    latestOnText.current = onText;
  });
  useEffect(
    () => () => {
      const rec = current.current;
      current.current = null;
      rec?.abort();
    },
    [],
  );

  function start() {
    const Recognition = recognitionCtor();
    if (!Recognition || current.current) return;
    const rec = new Recognition();
    rec.lang = lang;
    rec.continuous = false;
    rec.interimResults = true;
    // Anything from a recognition that was stopped or replaced is ignored.
    rec.onresult = (e) => {
      if (current.current !== rec) return;
      const spoken = transcriptOf(e.results);
      if (!spoken.trim()) return;
      setHeard(true);
      latestOnText.current(spoken);
    };
    rec.onerror = (e) => {
      if (current.current === rec) setProblem(speechProblem(e.error));
    };
    rec.onend = () => {
      if (current.current !== rec) return;
      current.current = null;
      setListening(false);
    };
    setProblem(null);
    setHeard(false);
    current.current = rec;
    try {
      rec.start();
      setListening(true);
    } catch {
      current.current = null;
      setProblem("other");
    }
  }

  /** Stop listening and keep what was heard (the last words may still arrive). */
  function stop() {
    current.current?.stop();
  }

  /** Stop listening and drop whatever was still on its way, for when the visitor types instead. */
  function cancel() {
    const rec = current.current;
    if (!rec) return;
    current.current = null;
    setListening(false);
    rec.abort();
  }

  return { supported, listening, heard, problem, start, stop, cancel };
}
