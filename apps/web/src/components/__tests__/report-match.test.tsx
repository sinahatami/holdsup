import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ReportMatch } from "@/components/organisms/report-match";
import { strings } from "@/lib/strings";

const t = strings.report;

const fetchMock = vi.fn();

function answer(status: number, body: unknown) {
  fetchMock.mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: "",
    json: async () => body,
  });
}

const open = () => {
  render(<ReportMatch checkId="check-1" claimIndex={1} />);
  fireEvent.click(screen.getByRole("button", { name: t.open }));
};

const sentBody = () => JSON.parse(fetchMock.mock.calls[0][1].body as string);

beforeEach(() => {
  fetchMock.mockReset();
  answer(201, { id: "r1" });
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => vi.unstubAllGlobals());

describe("ReportMatch", () => {
  it("starts as a single button that says it opens something", () => {
    render(<ReportMatch checkId="check-1" claimIndex={0} />);
    const button = screen.getByRole("button", { name: t.open });
    expect(button).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("group")).not.toBeInTheDocument();
  });

  it("opens a form in place and moves focus to its first choice", () => {
    open();
    expect(screen.getByRole("button", { name: t.open })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    const group = screen.getByRole("group", { name: t.heading });
    const choices = within(group).getAllByRole("radio");
    expect(choices.map((c) => (c as HTMLInputElement).value)).toEqual([
      "wrong_series",
      "wrong_reading",
      "other",
    ]);
    expect(choices[0]).toBeChecked();
    expect(choices[0]).toHaveFocus();
  });

  it("is anonymous, and says not to add personal details", () => {
    open();
    expect(screen.getByText(t.anonymous)).toBeInTheDocument();
    expect(screen.getByLabelText(t.noteLabel)).toHaveAccessibleDescription(
      t.anonymous,
    );
  });

  it("sends the kind, the claim and the trimmed note, then says it was recorded", async () => {
    open();
    fireEvent.click(screen.getByRole("radio", { name: t.kinds.wrong_reading }));
    fireEvent.change(screen.getByLabelText(t.noteLabel), {
      target: { value: "  The period is 2020, not 2021.  " },
    });
    fireEvent.click(screen.getByRole("button", { name: t.send }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toMatch(/\/v1\/checks\/check-1\/reports$/);
    expect(init.method).toBe("POST");
    expect(sentBody()).toEqual({
      kind: "wrong_reading",
      claim_index: 1,
      note: "The period is 2020, not 2021.",
    });
    expect(await screen.findByRole("status")).toHaveTextContent(t.thanks);
    // Nothing left to press: it was sent.
    expect(
      screen.queryByRole("button", { name: t.open }),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole("group")).not.toBeInTheDocument();
  });

  it("sends a report with no note", async () => {
    open();
    fireEvent.click(screen.getByRole("button", { name: t.send }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(sentBody()).toEqual({
      kind: "wrong_series",
      claim_index: 1,
      note: "",
    });
  });

  it("shows the reason when the API refuses, and lets the reader try again", async () => {
    answer(429, {
      type: "/problems/rate-limited",
      title: "Too many reports",
      status: 429,
      detail: "This address has sent too many reports this hour.",
    });
    open();
    fireEvent.click(screen.getByRole("button", { name: t.send }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "This address has sent too many reports this hour.",
    );
    // The form and what was typed are still there.
    expect(screen.getByRole("button", { name: t.send })).toBeEnabled();
    answer(201, { id: "r2" });
    fireEvent.click(screen.getByRole("button", { name: t.send }));
    expect(await screen.findByText(t.thanks)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("says so when the API cannot be reached", async () => {
    fetchMock.mockRejectedValue(new Error("down"));
    open();
    fireEvent.click(screen.getByRole("button", { name: t.send }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      strings.errors.network,
    );
  });

  it("does not send twice while the first is on its way", async () => {
    let finish: (v: unknown) => void = () => {};
    fetchMock.mockReturnValue(
      new Promise((resolve) => {
        finish = resolve;
      }),
    );
    open();
    const send = screen.getByRole("button", { name: t.send });
    fireEvent.click(send);
    expect(
      await screen.findByRole("button", { name: t.sending }),
    ).toBeDisabled();
    fireEvent.submit(send.closest("form") as HTMLFormElement);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    finish({ ok: true, status: 201, json: async () => ({ id: "r" }) });
    expect(await screen.findByText(t.thanks)).toBeInTheDocument();
  });

  it("closes without sending, and gives focus back to the button", () => {
    open();
    fireEvent.click(screen.getByRole("button", { name: t.cancel }));
    expect(screen.queryByRole("group")).not.toBeInTheDocument();
    const toggle = screen.getByRole("button", { name: t.open });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(toggle).toHaveFocus();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("closes again from the button that opened it", () => {
    open();
    fireEvent.click(screen.getByRole("button", { name: t.open }));
    expect(screen.queryByRole("group")).not.toBeInTheDocument();
  });

  it("limits the note to what the API takes, and counts it", () => {
    open();
    const box = screen.getByLabelText(t.noteLabel);
    expect(box).toHaveAttribute("maxlength", String(t.maxNote));
    fireEvent.change(box, { target: { value: "x".repeat(450) } });
    expect(screen.getByText(/450 \/ 500/)).toBeInTheDocument();
  });

  it("keeps two claims' forms apart", () => {
    render(
      <>
        <ReportMatch checkId="c" claimIndex={0} />
        <ReportMatch checkId="c" claimIndex={1} />
      </>,
    );
    const [first, second] = screen.getAllByRole("button", { name: t.open });
    fireEvent.click(first);
    fireEvent.click(second);
    const ids = [...document.querySelectorAll("[id]")].map((e) => e.id);
    expect(new Set(ids).size).toBe(ids.length);
    const names = screen
      .getAllByRole("radio")
      .map((r) => (r as HTMLInputElement).name);
    expect(new Set(names).size).toBe(2);
  });
});
