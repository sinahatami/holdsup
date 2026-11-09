import { afterEach, describe, expect, it, vi } from "vitest";
import { readCheck } from "@/lib/api/check";

const view = {
  id: "c1",
  text: "Debt is 133% of GDP.",
  status: "done",
  created_at: "",
  finished_at: "",
  result: null,
  error: null,
};

function answer(status: number, body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: status >= 200 && status < 300,
      status,
      statusText: "",
      json: async () => body,
    }),
  );
}

describe("readCheck", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("returns the check the API stored", async () => {
    answer(200, view);
    expect(await readCheck("c1")).toEqual({ kind: "found", view });
  });

  it("asks for the check by id, with a time limit", async () => {
    answer(200, view);
    await readCheck("c2");
    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(String(url)).toMatch(/\/v1\/checks\/c2$/);
    expect(init?.signal).toBeInstanceOf(AbortSignal);
  });

  it.each([404, 422])(
    "calls an id the API answers %i for missing",
    async (status) => {
      answer(status, { type: "about:blank", title: "No", status });
      expect(await readCheck(`m${status}`)).toEqual({ kind: "missing" });
    },
  );

  it("leaves the check to the browser when the API fails or is down", async () => {
    answer(503, { type: "about:blank", title: "Down", status: 503 });
    expect(await readCheck("u503")).toEqual({ kind: "unavailable" });
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("refused")));
    expect(await readCheck("ucrash")).toEqual({ kind: "unavailable" });
  });
});
