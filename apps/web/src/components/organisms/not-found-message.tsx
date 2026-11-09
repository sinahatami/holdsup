import Link from "next/link";
import { pill } from "@/components/atoms/pill";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

/** What a 404 page says: the code, what is missing, and the way back to checking a claim. */
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
    </>
  );
}
