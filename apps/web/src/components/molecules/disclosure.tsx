"use client";

import { ChevronDown } from "lucide-react";
import { useEffect, useRef, type ReactNode } from "react";

/**
 * A page section that starts folded: its heading is the button, so it is named like any
 * other section. A link to its id (`#id`), on arrival or later, opens it and scrolls to it,
 * because a browser does not open a closed `<details>` by itself.
 */
export function Disclosure({
  id,
  title,
  className,
  children,
}: {
  id: string;
  title: string;
  className?: string;
  children: ReactNode;
}) {
  const details = useRef<HTMLDetailsElement>(null);
  const headingId = `${id}-heading`;

  useEffect(() => {
    const openIfTargeted = () => {
      if (window.location.hash !== `#${id}` || !details.current) return;
      details.current.open = true;
      details.current.scrollIntoView();
    };
    openIfTargeted();
    window.addEventListener("hashchange", openIfTargeted);
    return () => window.removeEventListener("hashchange", openIfTargeted);
  }, [id]);

  return (
    <section id={id} aria-labelledby={headingId} className={className}>
      <details
        ref={details}
        className="group bg-background/50 rounded-2xl border p-5 open:shadow-(--shadow-soft)"
      >
        <summary className="flex cursor-pointer list-none items-center justify-between gap-3 [&::-webkit-details-marker]:hidden">
          <h2
            id={headingId}
            className="text-xl font-bold tracking-tight sm:text-2xl"
          >
            {title}
          </h2>
          <ChevronDown
            className="text-muted-foreground size-5 shrink-0 transition group-open:rotate-180"
            aria-hidden
          />
        </summary>
        <div className="mt-5 flex flex-col gap-5">{children}</div>
      </details>
    </section>
  );
}
