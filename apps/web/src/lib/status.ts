import type { ProviderStatus, StatusResponse } from "@/lib/api/client";
import { waitText } from "@/lib/format";
import { strings } from "@/lib/strings";

const t = strings.status;

/** A provider's state in words; a state that ends has its wait in it. */
export function stateText(p: ProviderStatus): string {
  switch (p.state) {
    case "cooling_down":
    case "failing":
    case "out_of_budget":
      return t.states[p.state](waitText(p.wait_s));
    default:
      return t.states[p.state]();
  }
}

/** The requests a provider has left today, or that it has no daily limit. */
export function leftText(p: ProviderStatus): string {
  return p.remaining_today === null || p.daily_cap === null
    ? t.noLimit
    : t.left(p.remaining_today, p.daily_cap);
}

/** The steps a provider serves, as the live trace names them. */
export function stepsText(p: ProviderStatus): string {
  const names = strings.steps as Record<string, string>;
  return p.steps.map((s) => names[s] ?? s).join(", ");
}

/** One sentence on whether checks can run now. */
export function statusSummary(status: StatusResponse): string {
  const ready = status.providers.filter((p) => p.state === "ready").length;
  return t.summary(ready, status.providers.length);
}
