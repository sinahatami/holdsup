import { cacheLife, cacheTag } from "next/cache";
import { afterEach, describe, expect, it, vi } from "vitest";
import { checkTag, readCheck, readNewer } from "@/lib/api/check";

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

describe("how long readCheck keeps a check", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.mocked(cacheLife).mockClear();
  });

  it("tags the read with the check, so the site can drop it", async () => {
    answer(200, view);
    await readCheck("t1");
    expect(cacheTag).toHaveBeenCalledWith(checkTag("t1"));
    expect(checkTag("t1")).toBe("check:t1");
  });

  it.each(["done", "failed"])(
    "keeps a %s check for days, so its page is stored whole",
    async (status) => {
      answer(200, { ...view, status });
      await readCheck(`k${status}`);
      expect(cacheLife).toHaveBeenCalledWith("days");
    },
  );

  it.each(["queued", "running"])(
    "keeps a %s check for seconds, out of any stored page",
    async (status) => {
      answer(200, { ...view, status });
      await readCheck(`s${status}`);
      expect(cacheLife).toHaveBeenCalledWith("seconds");
    },
  );

  it("keeps a missing check or a failed read for seconds", async () => {
    answer(404, { type: "about:blank", title: "No", status: 404 });
    await readCheck("s404");
    answer(503, { type: "about:blank", title: "Down", status: 503 });
    await readCheck("s503");
    expect(vi.mocked(cacheLife).mock.calls).toEqual([["seconds"], ["seconds"]]);
  });
});

describe("readNewer", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("gives the newer check's result, or only its id when it cannot be read", async () => {
    const result = { id: "n1", claims: [] };
    answer(200, { ...view, id: "n1", result });
    expect(await readNewer("n1")).toEqual({ id: "n1", result });
    answer(503, { type: "about:blank", title: "Down", status: 503 });
    expect(await readNewer("n2")).toEqual({ id: "n2", result: null });
  });
});
