import { NotFoundMessage } from "@/components/organisms/not-found-message";
import { PageShell } from "@/components/templates/page-shell";
import { strings } from "@/lib/strings";

/** A check link that points at nothing: a mistyped or cut-short address. */
export default function CheckNotFound() {
  return (
    <PageShell layout="message">
      <NotFoundMessage
        heading={strings.check.missing.heading}
        body={strings.check.missing.body}
      />
    </PageShell>
  );
}
