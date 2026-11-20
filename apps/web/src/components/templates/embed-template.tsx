import type { ReactNode } from "react";
import { LogoLockup } from "@/components/atoms/logo-lockup";
import { PageShell } from "@/components/templates/page-shell";
import { strings } from "@/lib/strings";

/**
 * A check inside another site's iframe: the name and tagline, so the reader knows whose
 * verdict it is, then the content, then a link out (`footer`) to HoldsUp itself. `aside`
 * takes the tagline's place (a check updated with revised figures says when), so the frame
 * keeps its height.
 */
export function EmbedTemplate({
  footer,
  aside,
  children,
}: {
  footer?: ReactNode;
  aside?: ReactNode;
  children: ReactNode;
}) {
  return (
    <PageShell layout="embed">
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 border-b pb-2">
        <h1>
          <LogoLockup label={strings.appName} className="h-6" />
        </h1>
        <p className="text-muted-foreground text-sm">
          {aside ?? strings.tagline}
        </p>
      </div>
      {children}
      {footer && <p className="text-sm">{footer}</p>}
    </PageShell>
  );
}
