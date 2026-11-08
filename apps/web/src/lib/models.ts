import type { ClaimResult, Step } from "@/lib/api/client";

type ModelUse = NonNullable<ClaimResult["models"]>[number];

export interface StepModels {
  step: Step;
  names: string[];
}

/** Pipeline order, so the receipt reads like the trace. */
const ORDER: Step[] = ["extract", "match", "plan", "explain"];

/**
 * The models behind a check, one row per step and each model named once, by its
 * readable label (older results have none, so the model id stands in).
 */
export function modelsByStep(uses: ModelUse[]): StepModels[] {
  const byStep = new Map<Step, string[]>();
  for (const use of uses) {
    const name = use.label || use.model;
    const names = byStep.get(use.step) ?? [];
    if (!names.includes(name)) names.push(name);
    byStep.set(use.step, names);
  }
  return [...byStep]
    .map(([step, names]) => ({ step, names }))
    .sort((a, b) => ORDER.indexOf(a.step) - ORDER.indexOf(b.step));
}
