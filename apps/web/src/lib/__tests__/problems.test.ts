import { afterEach, describe, expect, it, vi } from "vitest";
import {
  ApiError,
  REQUEST_TIMEOUT_MS,
  createApiClient,
  isRetryable,
  problemKind,
  problemText,
  toProblem,
  type Problem,
} from "@/lib/api/client";
import { strings } from "@/lib/strings";

const problem = (status: number, over: Partial<Problem> = {}): Problem => ({
  type: "about:blank",
  title: "Title",
  status,
  ...over,
});

afterEach(() => vi.unstubAllGlobals());

describe("problemKind", () => {
  it.each([
    [0, "network"],
    [429, "rate_limited"],
    [500, "unavailable"],
    [503, "unavailable"],
    [504, "unavailable"],
    [400, "other"],
    [404, "other"],
    [422, "other"],
  ] as const)("reads status %i as %s", (status, kind) => {
    expect(problemKind(problem(status))).toBe(kind);
  });

  it("recognises the timeout the client raises itself", () => {
    expect(
      problemKind(toProblem(new DOMException("slow", "TimeoutError"))),
    ).toBe("timeout");
  });
});

describe("isRetryable", () => {
  it("is true when trying again can help, and false for a text the API refused", () => {
    for (const status of [0, 429, 502, 503]) {
      expect(isRetryable(problem(status))).toBe(true);
    }
    for (const status of [400, 404, 422]) {
      expect(isRetryable(problem(status))).toBe(false);
    }
  });
});

describe("problemText", () => {
  it("is the API's detail, then when to try again if it says", () => {
    expect(
      problemText(problem(503, { detail: "All providers are busy." })),
    ).toBe("All providers are busy.");
    expect(
      problemText(problem(429, { detail: "Hourly limit.", retry_after: 30 })),
    ).toBe(`Hourly limit. ${strings.check.retryAfter(30)}`);
  });

  it("falls back to the title", () => {
    expect(problemText(problem(503))).toBe("Title");
  });
});

describe("toProblem", () => {
  it("keeps the API's own problem", () => {
    const own = problem(429);
    expect(toProblem(new ApiError(own))).toBe(own);
  });

  it("says a timeout and a lost network apart, in words a person can act on", () => {
    expect(toProblem(new DOMException("slow", "TimeoutError")).title).toBe(
      strings.errors.timeout,
    );
    expect(toProblem(new TypeError("Failed to fetch")).title).toBe(
      strings.errors.network,
    );
  });
});

describe("a request to the API", () => {
  const fetchOnce = (result: Promise<Response>) => {
    const fetchMock = vi.fn(() => result);
    vi.stubGlobal("fetch", fetchMock);
    return fetchMock;
  };

  it("gives up after a while instead of waiting for ever", async () => {
    const fetchMock = fetchOnce(
      Promise.reject(new DOMException("slow", "TimeoutError")),
    );
    const err = await createApiClient("http://api.test")
      .getCheck("c1")
      .catch((e: unknown) => e);
    const [, init] = fetchMock.mock.calls[0] as unknown as [
      string,
      RequestInit,
    ];
    expect(init.signal).toBeInstanceOf(AbortSignal);
    expect(REQUEST_TIMEOUT_MS).toBeGreaterThan(0);
    expect(problemKind(toProblem(err))).toBe("timeout");
  });

  it("lets a caller's own signal replace the default", async () => {
    const own = AbortSignal.timeout(5_000);
    const fetchMock = fetchOnce(
      Promise.resolve(new Response("{}", { status: 200 })),
    );
    await createApiClient("http://api.test").getCheck("c1", { signal: own });
    const [, init] = fetchMock.mock.calls[0] as unknown as [
      string,
      RequestInit,
    ];
    expect(init.signal).toBe(own);
  });
});
