import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/** A form control with its visible label above it and an optional hint below. */
export function Field({
  label,
  htmlFor,
  hint,
  hintId,
  className,
  children,
}: {
  label: string;
  /** The id of the control inside, so clicking the label focuses it. */
  htmlFor: string;
  hint?: string;
  /** The id the control's `aria-describedby` points at, when there is a hint. */
  hintId?: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <label htmlFor={htmlFor} className="text-sm font-medium">
        {label}
      </label>
      {children}
      {hint && (
        <p id={hintId} className="text-muted-foreground text-xs">
          {hint}
        </p>
      )}
    </div>
  );
}
