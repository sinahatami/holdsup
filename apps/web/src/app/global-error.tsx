"use client";

import "./globals.css";
import { strings } from "@/lib/strings";

/** The last resort, when even the layout fails: it brings its own page around the message. */
export default function GlobalError({ reset }: { reset: () => void }) {
  const t = strings.error;
  return (
    <html lang={strings.locale} dir={strings.dir}>
      <body className="flex min-h-full flex-col items-center justify-center gap-5 px-6 py-24 text-center">
        <h1 className="text-2xl font-bold">{t.heading}</h1>
        <p className="text-muted-foreground max-w-md">{t.body}</p>
        <button
          type="button"
          onClick={reset}
          className="bg-primary text-primary-foreground min-h-11 rounded-full px-6 py-3 font-semibold"
        >
          {t.retry}
        </button>
      </body>
    </html>
  );
}
