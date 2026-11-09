import { ArrowUpRight } from "lucide-react";
import type { ReactNode } from "react";
import { strings } from "@/lib/strings";
import { cn } from "@/lib/utils";

/**
 * A link to a page outside HoldsUp, such as a source's data or the repository. It
 * always opens in a new tab, so the reader keeps their place, and says so to a screen
 * reader. Every link off the site goes through here.
 *
 * `plain` leaves the look to the caller (a footer link, a button, an icon): no
 * underline, no arrow, only the new-tab behaviour and the spoken note.
 */
export function ExternalLink({
  href,
  className,
  plain = false,
  children,
}: {
  href: string;
  className?: string;
  plain?: boolean;
  children: ReactNode;
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={cn(
        !plain && "text-brand font-medium underline underline-offset-4",
        className,
      )}
    >
      {children}
      {!plain && (
        <ArrowUpRight className="inline size-3.5 align-text-top" aria-hidden />
      )}{" "}
      <span className="sr-only">{strings.receipt.opensInNewTab}</span>
    </a>
  );
}
