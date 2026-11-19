import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * A section's title in the display serif: the claim card's parts (the series, other time
 * windows, the receipt) and the benchmark's. Medium weight, like every heading in the serif.
 */
export function SectionTitle({
  as: Tag = "h3",
  id,
  className,
  children,
}: {
  as?: "h2" | "h3";
  id?: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <Tag
      id={id}
      className={cn(
        "font-heading text-[1.75rem] leading-tight font-medium tracking-[-0.01em] [font-synthesis:none]",
        className,
      )}
    >
      {children}
    </Tag>
  );
}
