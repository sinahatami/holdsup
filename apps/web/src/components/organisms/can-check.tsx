import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { TitledSection } from "@/components/molecules/titled-section";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

/** Home-page pointer to the full list of statistics HoldsUp can check. */
export function CanCheck() {
  return (
    <TitledSection id="can-check" title={strings.home.canCheckHeading}>
      <p className="text-muted-foreground leading-7">
        {strings.home.canCheckBody}
      </p>
      <Link
        href={routes.indicators}
        className="text-brand inline-flex items-center gap-2 text-sm font-semibold hover:underline"
      >
        {strings.home.canCheckLink}
        <ArrowRight className="size-4" aria-hidden />
      </Link>
    </TitledSection>
  );
}
