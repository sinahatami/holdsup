import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { pill } from "@/components/atoms/pill";
import { cn } from "@/lib/utils";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

/**
 * Back to the home page to check another claim. The arrow flips in RTL. Its own width, even
 * as a child of a column that stretches its children.
 */
export function BackLink() {
  return (
    <Link
      className={cn(pill({ tone: "glass" }), "self-start")}
      href={routes.home}
    >
      <ArrowLeft className="size-4 rtl:rotate-180" aria-hidden />
      {strings.check.back}
    </Link>
  );
}
