import type { BenchmarkRun, Rate } from "@/lib/api/client";
import { strings } from "@/lib/strings";

const t = strings.benchmark;

/** "63.2%", or "—" when nothing was measured. */
export function percent(rate: Rate): string {
  return rate.rate === null ? "—" : `${(rate.rate * 100).toFixed(1)}%`;
}

/** "63.2% (48 of 76)": the figure and what it is of, so a small sample is plain to see. */
export function rateText(rate: Rate): string {
  return rate.rate === null
    ? "—"
    : `${percent(rate)} (${rate.hits} of ${rate.total})`;
}

/** The share as a CSS length for a bar: 0 when nothing was measured. */
export function barWidth(rate: Rate): string {
  return `${Math.round((rate.rate ?? 0) * 100)}%`;
}

/** A verdict label, a pipeline step or "missed" in words; an unknown one stands as it is. */
export function labelText(label: string): string {
  const known: Record<string, string> = t.answers;
  return known[label] ?? label;
}

export function stepText(step: string): string {
  const known: Record<string, string> = t.steps;
  return known[step] ?? step;
}

/** Who answered a run: each model once by its readable name, most calls first. */
export function modelsText(run: BenchmarkRun): string {
  const names = run.models.map((m) => m.label);
  return names.length === 0 ? "—" : names.join(", ");
}

/** What a run is, in a few words: the pipeline or the chatbot, and the one provider if forced. */
export function runTitle(run: BenchmarkRun): string {
  const who = run.kind === "chatbot" ? t.who.chatbot : t.who.holdsup;
  return run.provider === "router" ? who : t.runOn(who, modelsText(run));
}

/** The split in words: the one the models were tuned on, or the held-out one. */
export function splitText(split: string): string {
  return split === "test" ? t.splits.test : t.splits.dev;
}
