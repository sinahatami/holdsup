import { describe, expect, it } from "vitest";
import { modelsByStep } from "@/lib/models";

const use = (step: "extract" | "match" | "plan" | "explain", label: string) =>
  ({ step, provider: "p", model: "id", label }) as const;

describe("modelsByStep", () => {
  it("orders steps like the pipeline and names each model once", () => {
    const rows = modelsByStep([
      use("explain", "B"),
      use("match", "A"),
      use("match", "A"),
      use("match", "C"),
      use("extract", ""),
    ]);
    expect(rows).toEqual([
      { step: "extract", names: ["id"] },
      { step: "match", names: ["A", "C"] },
      { step: "explain", names: ["B"] },
    ]);
  });
});
