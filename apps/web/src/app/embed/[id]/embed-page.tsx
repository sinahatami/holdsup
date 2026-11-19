import { notFound } from "next/navigation";
import { ExternalLink } from "@/components/atoms/external-link";
import { VerdictWidget } from "@/components/organisms/verdict-widget";
import { EmbedTemplate } from "@/components/templates/embed-template";
import { readCheck, type CheckLookup } from "@/lib/api/check";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

const t = strings.embed;

/** Why there is no verdict to show yet: still running, failed, empty or unreadable. */
function waiting(found: Exclude<CheckLookup, { kind: "missing" }>): string {
  if (found.kind === "unavailable") return t.unavailable;
  const { status, result } = found.view;
  if (result) return t.noClaims;
  return status === "failed" ? t.failed : t.running;
}

/**
 * A check's verdict for an iframe on another site, drawn on the server from what the API
 * holds now. A check with no verdict yet says why and links to its page, where it can be
 * followed live; every link opens HoldsUp in a new tab.
 */
export async function EmbedPage({ id }: { id: string }) {
  const found = await readCheck(id);
  if (found.kind === "missing") notFound();
  const result = found.kind === "found" ? found.view.result : null;
  if (result && result.claims.length > 0) {
    return (
      <EmbedTemplate
        footer={
          <ExternalLink href={routes.check(id)}>{t.fullReceipt}</ExternalLink>
        }
      >
        <VerdictWidget result={result} />
      </EmbedTemplate>
    );
  }
  return (
    <EmbedTemplate
      footer={
        <ExternalLink href={routes.check(id)}>{t.openCheck}</ExternalLink>
      }
    >
      <p className="text-muted-foreground">{waiting(found)}</p>
    </EmbedTemplate>
  );
}
