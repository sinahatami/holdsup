import {
  act,
  fireEvent,
  render,
  renderHook,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import GlobalError from "@/app/global-error";
import ErrorPage from "@/app/error";
import { OfflineNotice } from "@/components/molecules/offline-notice";
import { ProblemAlert } from "@/components/molecules/problem-alert";
import { RetryButton } from "@/components/molecules/retry-button";
import { CheckReport } from "@/components/organisms/check-report";
import type { CheckState } from "@/hooks/use-check";
import { useCheck } from "@/hooks/use-check";
import {
  ApiError,
  browserApi,
  type ApiClient,
  type Problem,
} from "@/lib/api/client";
import { strings } from "@/lib/strings";
import { checkResult, checkView, holdingClaim } from "@/test/fixtures";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

const t = strings.problem;
const problem = (status: number, over: Partial<Problem> = {}): Problem => ({
  type: "about:blank",
  title: "Title",
  status,
  ...over,
});

beforeEach(() => push.mockReset());
afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("ProblemAlert", () => {
  it.each([
    [0, t.heading.network],
    [429, t.heading.rate_limited],
    [503, t.heading.unavailable],
    [422, t.heading.other],
  ])("titles a status %i failure to fit it", (status, heading) => {
    render(<ProblemAlert problem={problem(status)} />);
    expect(screen.getByRole("heading", { name: heading })).toBeInTheDocument();
  });

  it("says when to try again, and shows what the reader can do about it", () => {
    render(
      <ProblemAlert
        problem={problem(429, { detail: "Too many.", retry_after: 30 })}
        action={<button type="button">Do it</button>}
      />,
    );
    expect(screen.getByText("Too many.")).toBeInTheDocument();
    expect(screen.getByText(strings.check.retryAfter(30))).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Do it" })).toBeInTheDocument();
  });
});

describe("RetryButton", () => {
  it("sends the same text again and opens the new check", async () => {
    const submit = vi
      .spyOn(browserApi, "submitCheck")
      .mockResolvedValue({ id: "new-1" } as never);
    render(<RetryButton text="Debt is 133% of GDP." />);
    fireEvent.click(screen.getByRole("button", { name: t.retry }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/check/new-1"));
    expect(submit).toHaveBeenCalledWith("Debt is 133% of GDP.");
  });

  it("waits out the time the API asked for, counting down, then lets it be pressed", () => {
    vi.useFakeTimers();
    render(<RetryButton text="x" retryAfter={3} />);
    const button = () => screen.getByRole("button");
    expect(button()).toBeDisabled();
    expect(button()).toHaveTextContent(t.retryIn(3));
    act(() => vi.advanceTimersByTime(1000));
    expect(button()).toHaveTextContent(t.retryIn(2));
    act(() => vi.advanceTimersByTime(1000));
    expect(button()).toHaveTextContent(t.retryIn(1));
    act(() => vi.advanceTimersByTime(1000));
    expect(button()).toBeEnabled();
    expect(button()).toHaveTextContent(t.retry);
  });

  it("says why when the new try fails too, and can be pressed again", async () => {
    vi.spyOn(browserApi, "submitCheck").mockRejectedValue(
      new ApiError(problem(429, { detail: "Hourly limit.", retry_after: 20 })),
    );
    render(<RetryButton text="x" />);
    fireEvent.click(screen.getByRole("button"));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      `Hourly limit. ${strings.check.retryAfter(20)}`,
    );
    expect(screen.getByRole("button")).toBeEnabled();
  });
});

const state = (over: Partial<CheckState>): CheckState => ({
  loading: false,
  text: "Debt is 133% of GDP.",
  trace: [],
  result: null,
  error: null,
  connectionLost: false,
  ...over,
});

describe("CheckReport when something goes wrong", () => {
  it("offers to try the same text again after a failure that trying again can fix", () => {
    render(<CheckReport state={state({ error: problem(503) })} />);
    expect(screen.getByRole("button", { name: t.retry })).toBeInTheDocument();
  });

  it("does not offer it for a text the API refused as it is", () => {
    render(<CheckReport state={state({ error: problem(422) })} />);
    expect(
      screen.queryByRole("button", { name: t.retry }),
    ).not.toBeInTheDocument();
  });

  it("has nothing to send again when the text is unknown", () => {
    render(<CheckReport state={state({ error: problem(503), text: null })} />);
    expect(
      screen.queryByRole("button", { name: t.retry }),
    ).not.toBeInTheDocument();
  });

  it("offers to reconnect when the live trace was lost, and does so on request", () => {
    const onReconnect = vi.fn();
    render(
      <CheckReport
        state={state({ connectionLost: true })}
        onReconnect={onReconnect}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      strings.check.connectionLost,
    );
    fireEvent.click(screen.getByRole("button", { name: t.reconnect }));
    expect(onReconnect).toHaveBeenCalledOnce();
  });

  it("drops the lost-connection notice once the result is in", () => {
    render(
      <CheckReport
        state={state({
          connectionLost: true,
          result: checkResult([holdingClaim]),
        })}
        onReconnect={() => {}}
      />,
    );
    expect(
      screen.queryByText(strings.check.connectionLost),
    ).not.toBeInTheDocument();
  });
});

describe("useCheck's reconnect", () => {
  it("starts again from the check as the server has it", async () => {
    let handlers: Parameters<ApiClient["follow"]>[1] | undefined;
    const stop = vi.fn();
    const api = {
      getCheck: vi
        .fn()
        .mockResolvedValue(
          checkView({ status: "running", text: "Debt is 133%." }),
        ),
      follow: vi.fn((_id: string, on: Parameters<ApiClient["follow"]>[1]) => {
        handlers = on;
        return stop;
      }),
    } as unknown as ApiClient;

    const { result } = renderHook(() => useCheck("c1", api));
    await waitFor(() => expect(api.follow).toHaveBeenCalledTimes(1));
    expect(result.current.state.text).toBe("Debt is 133%.");
    act(() => handlers!.onConnectionLost());
    expect(result.current.state.connectionLost).toBe(true);

    act(() => result.current.reconnect());
    await waitFor(() => expect(api.follow).toHaveBeenCalledTimes(2));
    expect(api.getCheck).toHaveBeenCalledTimes(2);
    expect(stop).toHaveBeenCalled();
    expect(result.current.state.connectionLost).toBe(false);
  });
});

describe("OfflineNotice", () => {
  it("shows nothing while online, and a notice while offline", () => {
    const online = vi.spyOn(navigator, "onLine", "get").mockReturnValue(true);
    const { container } = render(<OfflineNotice />);
    expect(container).toBeEmptyDOMElement();

    online.mockReturnValue(false);
    act(() => {
      window.dispatchEvent(new Event("offline"));
    });
    expect(screen.getByRole("alert")).toHaveTextContent(t.offline.heading);

    online.mockReturnValue(true);
    act(() => {
      window.dispatchEvent(new Event("online"));
    });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});

describe("the error pages", () => {
  it("lets a failed page try again, and logs what failed", () => {
    const log = vi.spyOn(console, "error").mockImplementation(() => {});
    const reset = vi.fn();
    const err = new Error("boom");
    render(<ErrorPage error={err} reset={reset} />);
    expect(
      screen.getByRole("heading", { name: strings.error.heading }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: strings.error.retry }));
    expect(reset).toHaveBeenCalledOnce();
    expect(log).toHaveBeenCalledWith(err);
    expect(
      screen.getByRole("link", { name: strings.check.back }),
    ).toHaveAttribute("href", "/");
  });

  it("brings its own page when even the layout fails", () => {
    const reset = vi.fn();
    render(<GlobalError reset={reset} />, {
      container: document.documentElement,
    });
    fireEvent.click(screen.getByRole("button", { name: strings.error.retry }));
    expect(reset).toHaveBeenCalledOnce();
  });
});
