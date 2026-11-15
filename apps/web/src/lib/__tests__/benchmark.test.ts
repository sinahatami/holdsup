import { describe, expect, it } from "vitest";
import {
  barWidth,
  labelText,
  modelsText,
  percent,
  rateText,
  runTitle,
  splitText,
  stepText,
} from "@/lib/benchmark";
import { benchmarkRun } from "@/test/fixtures";

describe("benchmark figures in words", () => {
  it("shows a share with what it is of, so a small sample is plain to see", () => {
    expect(percent({ hits: 36, total: 48, rate: 0.75 })).toBe("75.0%");
    expect(rateText({ hits: 36, total: 48, rate: 0.75 })).toBe(
      "75.0% (36 of 48)",
    );
  });

  it("shows nothing measured as a dash, never as 0%", () => {
    expect(percent({ hits: 0, total: 0, rate: null })).toBe("—");
    expect(rateText({ hits: 0, total: 0, rate: null })).toBe("—");
    expect(barWidth({ hits: 0, total: 0, rate: null })).toBe("0%");
    expect(barWidth({ hits: 3, total: 4, rate: 0.75 })).toBe("75%");
  });

  it("names verdicts and steps in words, and leaves an unknown one as it is", () => {
    expect(labelText("supported_framing_matters")).toBe(
      "Holds up, but the framing matters",
    );
    expect(labelText("missed")).toBe("No answer");
    expect(labelText("something_new")).toBe("something_new");
    expect(stepText("match")).toBe("Choosing the statistic");
    expect(stepText("something_new")).toBe("something_new");
  });

  it("names who answered a run, most calls first, and what the run is", () => {
    const run = benchmarkRun();
    expect(modelsText(run)).toBe(
      "GPT-OSS 120B (Groq), Ministral 14B (Mistral)",
    );
    expect(modelsText(benchmarkRun({ models: [] }))).toBe("—");
    expect(runTitle(run)).toBe("HoldsUp");
    expect(runTitle(benchmarkRun({ kind: "chatbot" }))).toBe("Plain chatbot");
    expect(
      runTitle(
        benchmarkRun({
          provider: "groq-gpt-oss-120b",
          models: [
            {
              provider: "groq-gpt-oss-120b",
              model: "m",
              label: "GPT-OSS",
              calls: 1,
            },
          ],
        }),
      ),
    ).toBe("HoldsUp, GPT-OSS only");
  });

  it("says which claims a split is", () => {
    expect(splitText("dev")).toBe("Development claims");
    expect(splitText("test")).toBe("Held-out claims");
  });
});
