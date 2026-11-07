import type { components } from "./schema";

export type CheckResult = components["schemas"]["CheckResult"];
export type ClaimResult = components["schemas"]["ClaimResult"];
export type CheckView = components["schemas"]["CheckView"];
export type CheckAccepted = components["schemas"]["CheckAccepted"];
export type GalleryItem = components["schemas"]["GalleryItem"];
export type Problem = components["schemas"]["Problem"];
export type Label = components["schemas"]["Label"];
export type Step = components["schemas"]["Step"];

/** One line of the live trace (the `step_started` / `step_done` event data). */
export interface StepEvent {
  event: "step_started" | "step_done";
  step: Step;
  claim: number | null;
  status: "ok" | "cant_check" | null;
  summary: string;
  models: string[];
  ms: number | null;
}

/** The browser talks to the API directly (CORS allows only the web origin). */
export function browserApiUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
}

/** Server-side reads (gallery pre-render) use the private variable when set. */
export function serverApiUrl(): string {
  return (
    process.env.HOLDSUP_API_URL ??
    process.env.NEXT_PUBLIC_API_URL ??
    "http://localhost:8000"
  );
}

export class ApiError extends Error {
  constructor(readonly problem: Problem) {
    super(problem.title);
  }
}

async function problemFrom(res: Response): Promise<Problem> {
  try {
    return (await res.json()) as Problem;
  } catch {
    return { type: "about:blank", title: res.statusText, status: res.status };
  }
}

export async function submitCheck(text: string): Promise<CheckAccepted> {
  const res = await fetch(`${browserApiUrl()}/v1/checks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new ApiError(await problemFrom(res));
  return (await res.json()) as CheckAccepted;
}

export async function getCheck(id: string): Promise<CheckView> {
  const res = await fetch(`${browserApiUrl()}/v1/checks/${id}`);
  if (!res.ok) throw new ApiError(await problemFrom(res));
  return (await res.json()) as CheckView;
}

export function streamUrl(id: string): string {
  return `${browserApiUrl()}/v1/checks/${id}/stream`;
}
