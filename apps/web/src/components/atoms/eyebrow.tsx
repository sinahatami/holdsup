import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/** A small upper-case heading that labels a block (trace, explanation, calculations). */
export function Eyebrow({
  as: Tag = "h2",
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
        "text-muted-foreground text-xs font-semibold tracking-widest uppercase",
        className,
      )}
    >
      {children}
    </Tag>
  );
}
