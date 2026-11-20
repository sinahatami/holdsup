import { notFound } from "next/navigation";
import { ExternalLink } from "@/components/atoms/external-link";
import { VerdictWidget } from "@/components/organisms/verdict-widget";
import { EmbedTemplate } from "@/components/templates/embed-template";
import { readCheck, type CheckLookup } from "@/lib/api/check";
import { formatDate } from "@/lib/format";
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
 * The check an embed shows: the one asked for, or the newest check computed again from it
 * after a source revised its figures (the claim watch, S1), so a widget stays current.
 */
async function newest(
  asked: Exclude<CheckLookup, { kind: "missing" }>,
): Promise<Exclude<CheckLookup, { kind: "missing" }>> {
  if (asked.kind !== "found" || !asked.view.updated_by) return asked;
  const newer = await readCheck(asked.view.updated_by);
  return newer.kind === "found" && newer.view.result ? newer : asked;
}

/**
 * A check's verdict for an iframe on another site, drawn on the server from what the API
 * holds now. A check with no verdict yet says why and links to its page, where it can be
 * followed live; every link opens HoldsUp in a new tab.
 */
export async function EmbedPage({ id }: { id: string }) {
  const asked = await readCheck(id);
  if (asked.kind === "missing") notFound();
  const found = await newest(asked);
  const shown = found !== asked && found.kind === "found" ? found.view.id : id;
  const result = found.kind === "found" ? found.view.result : null;
  if (result && result.claims.length > 0) {
    const updated = result.update_of
      ? strings.watch.embedUpdated(formatDate(result.created_at))
      : undefined;
    return (
      <EmbedTemplate
        aside={updated}
        footer={
          <ExternalLink href={routes.check(shown)}>
            {t.fullReceipt}
          </ExternalLink>
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
