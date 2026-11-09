import { ArrowUpRight } from "lucide-react";
import type { ReactNode } from "react";
import { strings } from "@/lib/strings";
import { cn } from "@/lib/utils";

/**
 * A link to a page outside HoldsUp, such as a source's data. It opens in a new
 * tab so the receipt stays where it was, and says so to a screen reader.
 */
export function ExternalLink({
  href,
  className,
  children,
}: {
  href: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={cn(
        "text-brand font-medium underline underline-offset-4",
        className,
      )}
    >
      {children}
      <ArrowUpRight className="inline size-3.5 align-text-top" aria-hidden />
      <span className="sr-only"> {strings.receipt.opensInNewTab}</span>
    </a>
  );
}
