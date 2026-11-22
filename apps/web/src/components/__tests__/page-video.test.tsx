import { render } from "@testing-library/react";
import { Activity } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PageVideo } from "@/components/atoms/page-video";

describe("PageVideo", () => {
  afterEach(() => vi.restoreAllMocks());

  it("pauses when its page is hidden, as Next does on leaving a page", () => {
    // jsdom does not play media; spy on pause to see it called.
    const pause = vi
      .spyOn(HTMLMediaElement.prototype, "pause")
      .mockImplementation(() => {});
    const page = (mode: "visible" | "hidden") => (
      <Activity mode={mode}>
        <PageVideo controls aria-label="tour" />
      </Activity>
    );
    const { container, rerender } = render(page("visible"));
    expect(container.querySelector("video")).toHaveAttribute("controls");
    expect(pause).not.toHaveBeenCalled();
    rerender(page("hidden"));
    expect(pause).toHaveBeenCalledTimes(1);
  });

  it("pauses when it unmounts", () => {
    const pause = vi
      .spyOn(HTMLMediaElement.prototype, "pause")
      .mockImplementation(() => {});
    const { unmount } = render(<PageVideo aria-label="tour" />);
    unmount();
    expect(pause).toHaveBeenCalledTimes(1);
  });
});
