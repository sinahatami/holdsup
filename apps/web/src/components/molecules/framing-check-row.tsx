import { StatusChip } from "@/components/atoms/status-chip";
import { verdictIcon } from "@/components/atoms/verdict-badge";
import type { DistortionCheck } from "@/lib/api/client";
import { strings } from "@/lib/strings";

const t = strings.framing;

/** The API writes each line as a clause for the verdict's reason; shown alone, it starts a sentence. */
function sentence(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1) + ".";
}

/**
 * One distortion check: what it looked at, whether it flags the claim, and the
 * line the code wrote with the numbers it computed. The result is said in words
 * and with an icon, so colour is never the only signal.
 */
export function FramingCheckRow({ check }: { check: DistortionCheck }) {
  const label = check.flagged ? "supported_framing_matters" : "supported";
  const Icon = verdictIcon[label];
  return (
    <li className="bg-card flex flex-col gap-2 border p-4">
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <p className="font-medium">{t.kinds[check.kind]}</p>
        <StatusChip verdict={label} icon={Icon}>
          {check.flagged ? t.flagged : t.passed}
        </StatusChip>
      </div>
      <p className="text-muted-foreground text-sm leading-6">
        {sentence(check.text)}
      </p>
    </li>
  );
}
