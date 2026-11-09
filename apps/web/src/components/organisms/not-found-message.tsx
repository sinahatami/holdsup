import Link from "next/link";
import { pill } from "@/components/atoms/pill";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

const around = [
  { href: routes.indicators, label: strings.nav.canCheck },
  { href: routes.recent, label: strings.nav.recent },
  { href: routes.methodology, label: strings.nav.methodology },
];

/**
 * What a 404 page says: the code, what is missing, the way back to checking a claim, and the
 * pages a visitor may have been after.
 */
export function NotFoundMessage({
  heading,
  body,
}: {
  heading: string;
  body: string;
}) {
  return (
    <>
      <p className="text-gradient text-8xl font-bold">
        {strings.notFound.code}
      </p>
      <h1 className="text-2xl font-bold">{heading}</h1>
      <p className="text-muted-foreground">{body}</p>
      <Link href={routes.home} className={pill({ tone: "primary" })}>
        {strings.check.back}
      </Link>
      <nav
        aria-label={strings.notFound.orTry}
        className="text-muted-foreground flex flex-wrap items-center justify-center gap-x-4 gap-y-2 text-sm"
      >
        <span>{strings.notFound.orTry}</span>
        {around.map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            className="text-brand font-medium underline underline-offset-4"
          >
            {label}
          </Link>
        ))}
      </nav>
    </>
  );
}
