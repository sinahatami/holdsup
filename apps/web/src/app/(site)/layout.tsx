import type { ReactNode } from "react";
import { SiteFrame } from "@/components/templates/site-frame";

/** The site's pages, each inside the header and footer. URLs leave out "(site)". */
export default function SiteLayout({ children }: { children: ReactNode }) {
  return <SiteFrame>{children}</SiteFrame>;
}
