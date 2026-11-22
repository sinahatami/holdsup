import { revalidatePath, revalidateTag } from "next/cache";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { POST } from "@/app/api/checks/[id]/refresh/route";

const ID = "4c47ae9e-0c31-4fbd-a132-aa05dfdfc109";

function refresh(id: string, query = "") {
  return POST(
    new Request(`http://site.test/api/checks/${id}/refresh${query}`, {
      method: "POST",
    }),
    { params: Promise.resolve({ id }) },
  );
}

beforeEach(() => {
  vi.mocked(revalidatePath).mockClear();
  vi.mocked(revalidateTag).mockClear();
});

describe("POST /api/checks/[id]/refresh", () => {
  it("expires the check's cached reads and its pages at once", async () => {
    const res = await refresh(ID);
    expect(res.status).toBe(204);
    expect(revalidateTag).toHaveBeenCalledExactlyOnceWith(`check:${ID}`, {
      expire: 0,
    });
    expect(vi.mocked(revalidatePath).mock.calls.map(([p]) => p)).toEqual([
      `/check/${ID}`,
      `/check/${ID}/opengraph-image`,
      `/embed/${ID}`,
    ]);
  });

  it("also expires the featured checks when asked", async () => {
    await refresh(ID, "?gallery=1");
    expect(revalidateTag).toHaveBeenCalledWith("gallery", { expire: 0 });
  });

  it("refuses what is not a check id, and expires nothing", async () => {
    const res = await refresh("../../home");
    expect(res.status).toBe(404);
    expect(revalidateTag).not.toHaveBeenCalled();
    expect(revalidatePath).not.toHaveBeenCalled();
  });
});
