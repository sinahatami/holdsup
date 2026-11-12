import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ClaimCard } from "@/components/organisms/claim-card";
import { CheckResultView } from "@/components/organisms/check-result";
import { browserApiUrl, type ClaimResult } from "@/lib/api/client";
import { historyStore } from "@/lib/history";
import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";
import {
  checkResult,
  holdingClaim,
  unmatchedClaim,
  versions,
} from "@/test/fixtures";

const push = vi.hoisted(() => vi.fn());
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

const t = strings.recheck;
const ILO = "Unemployment rate (ILO modelled estimate)";
const fetchMock = vi.fn();

function answer(status: number, body: unknown) {
  fetchMock.mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: "",
    headers: new Headers({ "content-type": "application/json" }),
    json: async () => body,
  });
}

const card = (claim: ClaimResult) =>
  render(
    <ClaimCard
      claim={claim}
      versions={versions}
      order={0}
      total={1}
      checkId="c1"
    />,
  );

beforeEach(() => {
  push.mockReset();
  fetchMock.mockReset();
  answer(202, {
    id: "c2",
    status: "queued",
    cached: false,
    stream_url: "/v1/checks/c2/stream",
    result_url: "/v1/checks/c2",
  });
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => vi.unstubAllGlobals());

describe("re-checking with another statistic", () => {
  it("offers the claim's other statistics under a checked claim", () => {
    card(holdingClaim);
    const section = within(screen.getByRole("region", { name: t.heading }));
    expect(section.getByText(t.intro)).toBeInTheDocument();
    expect(section.getByText(ILO)).toBeInTheDocument();
    expect(
      section.getByRole("button", { name: t.actionLabel(ILO) }),
    ).toHaveTextContent(t.action);
  });

  it("starts the re-check and opens the new check", async () => {
    const added = vi.spyOn(historyStore, "add");
    card(holdingClaim);
    fireEvent.click(screen.getByRole("button", { name: t.actionLabel(ILO) }));
    expect(
      screen.getByRole("button", { name: t.actionLabel(ILO) }),
    ).toBeDisabled();
    await waitFor(() => expect(push).toHaveBeenCalledWith(routes.check("c2")));
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${browserApiUrl()}/v1/checks/c1/claims/0/recheck`);
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({
      indicator_id: "unemployment_rate_ilo",
    });
    expect(added).toHaveBeenCalledWith("c2", holdingClaim.claim.quote);
  });

  it("says why when the re-check could not start, and lets the reader try again", async () => {
    answer(429, {
      type: "/problems/rate-limited",
      title: "Too many new checks",
      status: 429,
      detail: "This address has started too many new checks this hour.",
    });
    card(holdingClaim);
    const button = screen.getByRole("button", { name: t.actionLabel(ILO) });
    fireEvent.click(button);
    const section = within(screen.getByRole("region", { name: t.heading }));
    await waitFor(() =>
      expect(section.getByRole("status")).toHaveTextContent(/too many/i),
    );
    expect(button).toBeEnabled();
    expect(push).not.toHaveBeenCalled();
  });

  it("is left out when there is no other statistic", () => {
    card({ ...holdingClaim, suggestions: [] });
    expect(screen.queryByRole("region", { name: t.heading })).toBeNull();
  });

  it("puts a re-check beside each closest statistic of a claim that could not be checked", () => {
    card(unmatchedClaim);
    expect(screen.queryByRole("region", { name: t.heading })).toBeNull();
    const name = "Total population (Eurostat)";
    expect(
      screen.getByRole("button", { name: t.actionLabel(name) }),
    ).toBeInTheDocument();
  });

  it("says on the new check what it replaced, with a link back", () => {
    render(
      <CheckResultView
        result={{
          ...checkResult([holdingClaim], { id: "c2" }),
          recheck_of: {
            check_id: "c1",
            claim_index: 0,
            replaced: {
              id: "unemployment_rate_monthly",
              name: "Unemployment rate",
            },
          },
        }}
      />,
    );
    expect(
      screen.getByText(t.of("Unemployment rate"), { exact: false }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: t.back })).toHaveAttribute(
      "href",
      routes.check("c1"),
    );
  });
});
