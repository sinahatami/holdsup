import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/** One part of the receipt: a heading, then its content. The heading names the region. */
export function ReceiptSection({
  id,
  title,
  className,
  children,
}: {
  id: string;
  title: string;
  className?: string;
  children: ReactNode;
}) {
  const headingId = `${id}-heading`;
  return (
    <section
      aria-labelledby={headingId}
      className={cn("flex flex-col gap-3", className)}
    >
      <h4 id={headingId} className="text-base font-semibold">
        {title}
      </h4>
      {children}
    </section>
  );
}
