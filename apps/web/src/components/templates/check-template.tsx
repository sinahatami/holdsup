import type { ReactNode } from "react";
import { PageShell } from "@/components/templates/page-shell";
import { strings } from "@/lib/strings";

/**
 * The check page: its heading ("Check" unless told otherwise), optional actions beside it,
 * an optional line of facts under it (a receipt's number, date and claims), then the content.
 */
export function CheckTemplate({
  heading = strings.check.heading,
  facts,
  actions,
  children,
}: {
  heading?: string;
  facts?: readonly string[];
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <PageShell layout="content">
      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h1 className="text-gradient text-4xl">{heading}</h1>
          {actions}
        </div>
        {facts && facts.length > 0 && (
          <ul className="text-muted-foreground flex flex-wrap gap-x-3 gap-y-1 text-sm">
            {facts.map((f, i) => (
              <li
                key={f}
                className={
                  i === 0 ? "font-mono text-[0.8125rem] tracking-wide" : ""
                }
              >
                {i > 0 && (
                  <span aria-hidden className="me-3">
                    ·
                  </span>
                )}
                {f}
              </li>
            ))}
          </ul>
        )}
      </div>
      {children}
    </PageShell>
  );
}
