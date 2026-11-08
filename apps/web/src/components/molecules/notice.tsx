import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

/** A short alert line with an icon, e.g. a dropped live connection. */
export function Notice({
  icon: Icon,
  children,
}: {
  icon: LucideIcon;
  children: ReactNode;
}) {
  return (
    <p
      role="alert"
      className="glass flex items-center gap-2 rounded-2xl p-4 text-sm"
    >
      <Icon className="size-4" aria-hidden />
      {children}
    </p>
  );
}
