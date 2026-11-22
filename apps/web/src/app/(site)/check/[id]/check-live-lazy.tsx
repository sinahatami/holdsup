"use client";

import dynamic from "next/dynamic";

/**
 * CheckLive in a chunk of its own. A finished check is drawn on the server and never needs
 * the code that follows a running one (the trace, the progress steps and a client copy of
 * the receipt), so a result page no longer downloads it. Where a check is still running,
 * the server renders it as before and the chunk is preloaded with the page; while it loads
 * on a client navigation, the page's own loading frame shows (there is no fallback here).
 */
export const CheckLive = dynamic(() =>
  import("./check-live").then((m) => m.CheckLive),
);
