import { NotFoundMessage } from "@/components/organisms/not-found-message";
import { PageShell } from "@/components/templates/page-shell";
import { SiteFrame } from "@/components/templates/site-frame";
import { strings } from "@/lib/strings";

// An address that matches no page is drawn in the root layout, outside (site)/layout.tsx,
// so it brings the site's header and footer itself.
export default function NotFound() {
  return (
    <SiteFrame>
      <PageShell layout="message">
        <NotFoundMessage
          heading={strings.notFound.heading}
          body={strings.notFound.body}
        />
      </PageShell>
    </SiteFrame>
  );
}
