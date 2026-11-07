import type { Metadata } from "next";
import { CheckPage } from "@/components/check-page";
import { strings } from "@/lib/strings";

export const metadata: Metadata = {
  title: `${strings.check.heading} · ${strings.appName}`,
};

export default async function Page({ params }: PageProps<"/check/[id]">) {
  const { id } = await params;
  return <CheckPage id={id} />;
}
