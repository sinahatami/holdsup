import { ExternalLink } from "@/components/atoms/external-link";
import { EmbedTemplate } from "@/components/templates/embed-template";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

/** An embed of a check that does not exist: a mistyped or cut-short id in the frame's src. */
export default function EmbedNotFound() {
  return (
    <EmbedTemplate
      footer={
        <ExternalLink href={routes.home}>
          {strings.embed.openHoldsUp}
        </ExternalLink>
      }
    >
      <p className="text-muted-foreground">{strings.embed.missing}</p>
    </EmbedTemplate>
  );
}
