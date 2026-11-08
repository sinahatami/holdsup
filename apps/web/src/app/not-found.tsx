import Link from "next/link";
import { strings } from "@/lib/strings";

export default function NotFound() {
  return (
    <main className="mx-auto flex w-full max-w-xl flex-1 flex-col items-center justify-center gap-5 px-6 py-24 text-center">
      <p className="text-gradient text-8xl font-bold">404</p>
      <h1 className="text-2xl font-bold">{strings.notFound.heading}</h1>
      <p className="text-muted-foreground">{strings.notFound.body}</p>
      <Link
        href="/"
        className="bg-primary text-primary-foreground rounded-full px-6 py-2.5 font-semibold shadow-lg shadow-(color:--brand)/30"
      >
        {strings.check.back}
      </Link>
    </main>
  );
}
