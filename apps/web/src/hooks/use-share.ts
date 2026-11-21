"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { copyText } from "@/lib/clipboard";
import { shareSummary } from "@/lib/share";

/** What the last action did, for the status line: nothing yet, copied, or failed. */
export type ShareStatus = "link" | "summary" | "embed" | "failed" | null;

const STATUS_MS = 4000;
const noop = () => () => {};

/** This page's address, without a fragment or query: the permanent link of the check. */
const pageUrl = () => `${location.origin}${location.pathname}`;

/**
 * Copy and share actions for the check on this page, and the exact text each copy puts on
 * the clipboard, to show before it is copied. The address is only known in the browser, so
 * `url`, `summary` and `embedCode` are null on the server and before hydration; so is
 * `canShare` (whether the browser has the native share sheet) false. The status clears
 * itself after a few seconds.
 */
export function useShare(
  title: string,
  text: string,
  embed?: (origin: string) => string,
) {
  const [status, setStatus] = useState<ShareStatus>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const canShare = useSyncExternalStore(
    noop,
    () => typeof navigator.share === "function",
    () => false,
  );
  const url = useSyncExternalStore(noop, pageUrl, () => null);
  const origin = useSyncExternalStore(
    noop,
    () => location.origin,
    () => null,
  );
  const summary = url && shareSummary(text, url);
  const embedCode = (origin && embed?.(origin)) || null;

  useEffect(() => () => clearTimeout(timer.current), []);

  function announce(next: ShareStatus) {
    clearTimeout(timer.current);
    setStatus(next);
    timer.current = setTimeout(() => setStatus(null), STATUS_MS);
  }

  /** Copies one of the three texts; whether it worked (on failure, the status says so). */
  async function copy(what: "link" | "summary" | "embed"): Promise<boolean> {
    const value = { link: url, summary, embed: embedCode }[what];
    const ok = value !== null && (await copyText(value));
    announce(ok ? what : "failed");
    return ok;
  }

  async function share() {
    try {
      await navigator.share({ title, text, url: pageUrl() });
    } catch (err) {
      // Closing the share sheet is not a failure.
      if (!(err instanceof DOMException && err.name === "AbortError")) {
        announce("failed");
      }
    }
  }

  return {
    canShare,
    url,
    summary,
    embedCode,
    status,
    clearStatus: () => {
      clearTimeout(timer.current);
      setStatus(null);
    },
    copy,
    share,
  };
}
