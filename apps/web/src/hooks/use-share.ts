"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { copyText } from "@/lib/clipboard";
import { shareSummary } from "@/lib/share";

/** What the last action did, for the status line: nothing yet, copied, or failed. */
export type ShareStatus = "link" | "summary" | "failed" | null;

const STATUS_MS = 3000;
const noop = () => () => {};

/** This page's address, without a fragment or query: the permanent link of the check. */
const pageUrl = () => `${location.origin}${location.pathname}`;

/**
 * Copy and share actions for the check on this page. `canShare` is whether the
 * browser has the native share sheet; it is false until hydration, so the markup
 * always matches. The status clears itself after a few seconds.
 */
export function useShare(title: string, text: string) {
  const [status, setStatus] = useState<ShareStatus>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const canShare = useSyncExternalStore(
    noop,
    () => typeof navigator.share === "function",
    () => false,
  );

  useEffect(() => () => clearTimeout(timer.current), []);

  function announce(next: ShareStatus) {
    clearTimeout(timer.current);
    setStatus(next);
    timer.current = setTimeout(() => setStatus(null), STATUS_MS);
  }

  async function copy(what: "link" | "summary") {
    const url = pageUrl();
    const ok = await copyText(what === "link" ? url : shareSummary(text, url));
    announce(ok ? what : "failed");
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
    status,
    copyLink: () => copy("link"),
    copySummary: () => copy("summary"),
    share,
  };
}
