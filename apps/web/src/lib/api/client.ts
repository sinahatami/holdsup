import { strings } from "@/lib/strings";
import type { components } from "./schema";

export type CheckResult = components["schemas"]["CheckResult"];
export type ClaimResult = components["schemas"]["ClaimResult"];
export type ClaimSpec = components["schemas"]["ClaimSpec"];
/** One calculation a claim's receipt lists. */
export type Operation = NonNullable<ClaimResult["operations"]>[number];
/** One checked piece of a claim: the figures a verdict compared. */
export type Part = NonNullable<ClaimResult["verdict"]["parts"]>[number];
export type CheckView = components["schemas"]["CheckView"];
export type CheckAccepted = components["schemas"]["CheckAccepted"];
export type CatalogResponse = components["schemas"]["CatalogResponse"];
export type CatalogEntry = components["schemas"]["CatalogEntry"];
export type GalleryItem = components["schemas"]["GalleryItem"];
export type GalleryClaim = components["schemas"]["GalleryClaim"];
export type ReportKind = components["schemas"]["ReportKind"];
export type ReportRequest = components["schemas"]["ReportRequest"];
export type ReportAccepted = components["schemas"]["ReportAccepted"];
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

/** What a caller of {@link ApiClient.follow} hears while a check runs. */
export interface CheckStreamHandlers {
  onStep(event: StepEvent): void;
  onResult(result: CheckResult): void;
  onProblem(problem: Problem): void;
  onConnectionLost(): void;
}

const LOCAL_API = "http://localhost:8000";

/** The browser talks to the API directly (CORS allows only the web origin). */
export function browserApiUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? LOCAL_API;
}

/** Server-side reads (gallery pre-render) use the private variable when set. */
export function serverApiUrl(): string {
  return (
    process.env.HOLDSUP_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? LOCAL_API
  );
}

export class ApiError extends Error {
  constructor(readonly problem: Problem) {
    super(problem.title);
  }
}

/** The problem shown when the API could not be reached at all. */
export function networkProblem(): Problem {
  return { type: "about:blank", title: strings.errors.network, status: 0 };
}

/** Any thrown value as a problem: the API's own, or a network failure. */
export function toProblem(err: unknown): Problem {
  return err instanceof ApiError ? err.problem : networkProblem();
}

/** The one line a person should read about a problem. */
export function problemMessage(problem: Problem): string {
  return problem.detail ?? problem.title;
}

async function problemFrom(res: Response): Promise<Problem> {
  try {
    return (await res.json()) as Problem;
  } catch {
    return { type: "about:blank", title: res.statusText, status: res.status };
  }
}

function followStream(url: string, on: CheckStreamHandlers): () => void {
  const source = new EventSource(url);
  const parse = <T>(e: MessageEvent<string>) => JSON.parse(e.data) as T;
  const onStep = (e: MessageEvent<string>) => on.onStep(parse<StepEvent>(e));
  source.addEventListener("step_started", onStep);
  source.addEventListener("step_done", onStep);
  source.addEventListener("result", (e) => {
    on.onResult(parse<CheckResult>(e));
    source.close();
  });
  source.addEventListener("error", (e) => {
    if (e instanceof MessageEvent) {
      on.onProblem(parse<Problem>(e));
      source.close();
    } else if (source.readyState === EventSource.CLOSED) {
      on.onConnectionLost();
    }
  });
  return () => source.close();
}

/**
 * Factory for an API client bound to one base URL: the browser and the server
 * reach the API at different addresses but speak the same contract.
 */
export function createApiClient(baseUrl: string) {
  const url = (path: string) => `${baseUrl}/v1${path}`;

  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const res = await fetch(url(path), init);
    if (!res.ok) throw new ApiError(await problemFrom(res));
    return (await res.json()) as T;
  }

  return {
    submitCheck: (text: string) =>
      request<CheckAccepted>("/checks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      }),
    /** Tells the maintainers a check matched the wrong statistic or read a claim wrongly. */
    reportCheck: (id: string, report: ReportRequest) =>
      request<ReportAccepted>(`/checks/${id}/reports`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(report),
      }),
    catalog: () => request<CatalogResponse>("/catalog"),
    getCheck: (id: string, init?: RequestInit) =>
      request<CheckView>(`/checks/${id}`, init),
    gallery: async (limit: number) =>
      (await request<{ items: GalleryItem[] }>(`/gallery?limit=${limit}`))
        .items,
    /** Follows a running check's live trace; returns a function that stops. */
    follow: (id: string, on: CheckStreamHandlers) =>
      followStream(url(`/checks/${id}/stream`), on),
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;

/** The client components use by default. */
export const browserApi: ApiClient = createApiClient(browserApiUrl());
