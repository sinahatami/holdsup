import { describe, expect, it } from "vitest";
import type { ProviderStatus } from "@/lib/api/client";
import {
  leftText,
  stateText,
  statusSummary,
  stepsText,
  waitText,
} from "@/lib/status";
import { strings } from "@/lib/strings";
import { statusResponse } from "@/test/fixtures";

const t = strings.status;
const [groq, mistral, openrouter] = statusResponse.providers;

describe("status in words", () => {
  it("rounds a wait up to what a reader needs", () => {
    expect(waitText(0.2)).toBe("about 1 second");
    expect(waitText(14.2)).toBe("about 15 seconds");
    expect(waitText(61)).toBe("about 2 minutes");
    expect(waitText(7900)).toBe("about 2 hours");
    expect(waitText(3600)).toBe("about 1 hour");
  });

  it("says each state, with its wait when it ends", () => {
    expect(stateText(groq)).toBe("Ready");
    expect(stateText(mistral)).toBe("Cooling down, ready in about 15 seconds");
    expect(stateText(openrouter)).toBe(
      "Out of today's requests, back in about 2 hours",
    );
    const failing: ProviderStatus = { ...groq, state: "failing", wait_s: 50 };
    expect(stateText(failing)).toBe("Failing, tried again in about 50 seconds");
    expect(stateText({ ...groq, state: "not_configured" })).toBe(
      "Not set up on this server",
    );
  });

  it("says the requests left under the cap, or that there is no daily limit", () => {
    expect(leftText(groq)).toBe("812 of 900");
    expect(leftText(mistral)).toBe(t.noLimit);
  });

  it("names the steps as the live trace does", () => {
    expect(stepsText(mistral)).toBe(
      `${strings.steps.extract}, ${strings.steps.plan}`,
    );
    expect(stepsText({ ...groq, steps: ["eval"] })).toBe("eval");
  });

  it("says whether checks can run", () => {
    expect(statusSummary(statusResponse)).toBe(
      "1 of 3 providers are ready; checks use those.",
    );
    const ready = statusResponse.providers.map((p) => ({
      ...p,
      state: "ready" as const,
    }));
    expect(statusSummary({ ...statusResponse, providers: ready })).toBe(
      "All 3 providers are ready.",
    );
    expect(statusSummary({ ...statusResponse, providers: [openrouter] })).toBe(
      t.summary(0, 1),
    );
  });
});
