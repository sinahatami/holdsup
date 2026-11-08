import type { ReactNode } from "react";
import { PageShell } from "@/components/templates/page-shell";
import { strings } from "@/lib/strings";

/** The check page: its heading, optional actions beside it, then the content. */
export function CheckTemplate({
  actions,
  children,
}: {
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <PageShell layout="content">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-gradient text-4xl font-bold tracking-tight">
          {strings.check.heading}
        </h1>
        {actions}
      </div>
      {children}
    </PageShell>
  );
}
