import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { pill } from "@/components/atoms/pill";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

/** Back to the home page to check another claim. The arrow flips in RTL. */
export function BackLink() {
  return (
    <Link className={pill({ tone: "glass" })} href={routes.home}>
      <ArrowLeft className="size-4 rtl:rotate-180" aria-hidden />
      {strings.check.back}
    </Link>
  );
}
