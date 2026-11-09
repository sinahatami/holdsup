import { NotFoundMessage } from "@/components/organisms/not-found-message";
import { PageShell } from "@/components/templates/page-shell";
import { strings } from "@/lib/strings";

export default function NotFound() {
  return (
    <PageShell layout="message">
      <NotFoundMessage
        heading={strings.notFound.heading}
        body={strings.notFound.body}
      />
    </PageShell>
  );
}
