import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/** A page section named by its heading (`<id>-heading`), so landmarks are labelled. */
export function TitledSection({
  id,
  title,
  aside,
  className,
  children,
}: {
  id: string;
  title: string;
  /** Muted text beside the heading, such as a count. */
  aside?: string;
  className?: string;
  children: ReactNode;
}) {
  const headingId = `${id}-heading`;
  return (
    <section
      id={id}
      aria-labelledby={headingId}
      className={cn("flex flex-col gap-5", className)}
    >
      <div className="flex flex-wrap items-baseline gap-x-3">
        <h2 id={headingId} className="text-2xl font-bold tracking-tight">
          {title}
        </h2>
        {aside && (
          <span className="text-muted-foreground text-sm font-medium">
            {aside}
          </span>
        )}
      </div>
      {children}
    </section>
  );
}
