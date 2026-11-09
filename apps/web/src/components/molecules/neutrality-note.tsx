import { Info } from "lucide-react";
import Link from "next/link";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

/** Says a verdict judges the number, not the speaker, and where to read how. */
export function NeutralityNote() {
  const t = strings.home.neutrality;
  return (
    <p className="text-muted-foreground flex items-start gap-2 text-sm leading-6">
      <Info className="mt-1 size-4 shrink-0" aria-hidden />
      <span>
        {t.text}{" "}
        <Link
          href={routes.methodology}
          className="text-brand font-medium underline underline-offset-4"
        >
          {t.link}
        </Link>
      </span>
    </p>
  );
}
