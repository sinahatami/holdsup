"use client";

import Link from "next/link";
import { useEffect } from "react";
import { pill } from "@/components/atoms/pill";
import { PageShell } from "@/components/templates/page-shell";
import { routes } from "@/lib/routes";
import { boundaryStrings } from "@/lib/strings/boundary";

/** What a page shows when it fails while rendering: what happened, and a way to try again. */
export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);
  const t = boundaryStrings.error;
  return (
    <PageShell layout="message">
      <h1 className="text-2xl">{t.heading}</h1>
      <p className="text-muted-foreground">{t.body}</p>
      <div className="flex flex-wrap items-center justify-center gap-3">
        <button
          type="button"
          onClick={reset}
          className={pill({ tone: "primary" })}
        >
          {t.retry}
        </button>
        <Link href={routes.home} className={pill({ tone: "glass" })}>
          {boundaryStrings.back}
        </Link>
      </div>
    </PageShell>
  );
}
