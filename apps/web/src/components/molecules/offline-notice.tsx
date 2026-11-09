"use client";

import { WifiOff } from "lucide-react";
import { Notice } from "@/components/molecules/notice";
import { useOnline } from "@/hooks/use-online";
import { strings } from "@/lib/strings";

/** A line under the header while the browser has no connection; nothing when it has. */
export function OfflineNotice() {
  const online = useOnline();
  if (online) return null;
  const t = strings.problem.offline;
  return (
    <div className="mx-auto w-full max-w-3xl px-5 pt-4 sm:px-6">
      <Notice icon={WifiOff}>
        <span>
          <strong className="font-semibold">{t.heading}.</strong> {t.body}
        </span>
      </Notice>
    </div>
  );
}
