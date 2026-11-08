import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/** A page section named by its heading (`<id>-heading`), so landmarks are labelled. */
export function TitledSection({
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
      id={id}
      aria-labelledby={headingId}
      className={cn("flex flex-col gap-5", className)}
    >
      <h2 id={headingId} className="text-2xl font-bold tracking-tight">
        {title}
      </h2>
      {children}
    </section>
  );
}
