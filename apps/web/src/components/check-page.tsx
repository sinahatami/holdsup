"use client";

import { ArrowLeft, OctagonAlert, WifiOff } from "lucide-react";
import Link from "next/link";
import { CheckResultView } from "@/components/check-result";
import { Trace } from "@/components/trace";
import { useCheck } from "@/lib/use-check";
import { strings } from "@/lib/strings";

export function CheckPage({ id }: { id: string }) {
  const { loading, trace, result, error, connectionLost } = useCheck(id);
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-5 py-12 sm:px-6 sm:py-16">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-gradient text-4xl font-bold tracking-tight">
          {strings.check.heading}
        </h1>
        <Link
          className="glass hover:bg-accent inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition"
          href="/"
        >
          <ArrowLeft className="size-4 rtl:rotate-180" aria-hidden />
          {strings.check.back}
        </Link>
      </div>
      {loading && (
        <p role="status" className="text-muted-foreground animate-pulse">
          {strings.check.loading}
        </p>
      )}
      {error && (
        <div
          role="alert"
          data-verdict="not_supported"
          className="glass flex gap-3 rounded-2xl p-5"
          style={{
            borderColor: "color-mix(in oklch, var(--v) 40%, transparent)",
          }}
        >
          <OctagonAlert
            className="mt-0.5 size-5 shrink-0"
            style={{ color: "var(--v)" }}
            aria-hidden
          />
          <div>
            <h2 className="font-semibold">{strings.check.errorHeading}</h2>
            <p className="text-muted-foreground">
              {error.detail ?? error.title}
            </p>
            {error.retry_after ? (
              <p className="text-muted-foreground">
                {strings.check.retryAfter(error.retry_after)}
              </p>
            ) : null}
          </div>
        </div>
      )}
      {connectionLost && (
        <p
          role="alert"
          className="glass flex items-center gap-2 rounded-2xl p-4 text-sm"
        >
          <WifiOff className="size-4" aria-hidden />
          {strings.check.connectionLost}
        </p>
      )}
      <Trace rows={trace} />
      {result && <CheckResultView result={result} />}
    </main>
  );
}
