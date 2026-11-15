import Link from "next/link";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

/**
 * The app's name set as a fraction, "Holds" over a blue bar over "Up": every number has a
 * denominator. `badge` is the header's larger size; plain is the footer's.
 */
export function Logo({ variant = "plain" }: { variant?: "plain" | "badge" }) {
  const [top, bottom] = strings.logoParts;
  return (
    <Link
      href={routes.home}
      aria-label={strings.appName}
      className={
        variant === "badge"
          ? "font-heading inline-flex flex-col items-center text-xl leading-none"
          : "font-heading inline-flex flex-col items-center text-lg leading-none"
      }
    >
      <span aria-hidden>{top}</span>
      <span aria-hidden className="bg-brand my-[3px] block h-[3px] w-full" />
      <span aria-hidden>{bottom}</span>
    </Link>
  );
}
