"use client";

import Link from "next/link";
import { CheckResultView } from "@/components/check-result";
import { Trace } from "@/components/trace";
import { useCheck } from "@/lib/use-check";
import { strings } from "@/lib/strings";

export function CheckPage({ id }: { id: string }) {
  const { loading, trace, result, error, connectionLost } = useCheck(id);
  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-8 px-6 py-12">
      <h1 className="text-3xl font-semibold tracking-tight">
        {strings.check.heading}
      </h1>
      {loading && <p role="status">{strings.check.loading}</p>}
      {error && (
        <div role="alert" className="rounded-md border border-rose-700 p-4">
          <h2 className="font-semibold">{strings.check.errorHeading}</h2>
          <p>{error.detail ?? error.title}</p>
          {error.retry_after ? (
            <p>{strings.check.retryAfter(error.retry_after)}</p>
          ) : null}
        </div>
      )}
      {connectionLost && <p role="alert">{strings.check.connectionLost}</p>}
      <Trace rows={trace} />
      {result && <CheckResultView result={result} />}
      <Link className="underline" href="/">
        {strings.check.back}
      </Link>
    </main>
  );
}
