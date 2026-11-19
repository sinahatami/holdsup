import Link from "next/link";
import { LogoLockup } from "@/components/atoms/logo-lockup";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

/**
 * The logo as the home link. `badge` is the header's size, a step smaller on a phone so the
 * header's buttons still fit at 360 px; plain is the footer's.
 */
export function Logo({ variant = "plain" }: { variant?: "plain" | "badge" }) {
  return (
    <Link
      href={routes.home}
      aria-label={strings.appName}
      className="text-foreground inline-flex w-fit rounded-sm"
    >
      <LogoLockup
        className={variant === "badge" ? "h-6 sm:h-[1.875rem]" : "h-[1.625rem]"}
      />
    </Link>
  );
}
