import Link from "next/link";
import { pill } from "@/components/atoms/pill";
import { PageShell } from "@/components/templates/page-shell";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

export default function NotFound() {
  return (
    <PageShell layout="message">
      <p className="text-gradient text-8xl font-bold">
        {strings.notFound.code}
      </p>
      <h1 className="text-2xl font-bold">{strings.notFound.heading}</h1>
      <p className="text-muted-foreground">{strings.notFound.body}</p>
      <Link href={routes.home} className={pill({ tone: "primary" })}>
        {strings.check.back}
      </Link>
    </PageShell>
  );
}
