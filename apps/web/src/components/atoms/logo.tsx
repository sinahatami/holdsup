import { ShieldCheck } from "lucide-react";
import Link from "next/link";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

/** The app's mark and name, linking home. `badge` sets the mark on a filled tile. */
export function Logo({ variant = "plain" }: { variant?: "plain" | "badge" }) {
  if (variant === "badge") {
    return (
      <Link
        href={routes.home}
        className="flex items-center gap-2.5 font-bold tracking-tight"
      >
        <span className="bg-primary text-primary-foreground flex size-8 items-center justify-center rounded-xl shadow-md shadow-(color:--brand)/30">
          <ShieldCheck className="size-4.5" aria-hidden />
        </span>
        {strings.appName}
      </Link>
    );
  }
  return (
    <Link href={routes.home} className="flex items-center gap-2 font-bold">
      <ShieldCheck className="text-brand size-5" aria-hidden />
      {strings.appName}
    </Link>
  );
}
