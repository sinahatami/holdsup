import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  TOUR_POSTER,
  TOUR_VIDEO,
  TourVideo,
} from "@/components/molecules/tour-video";
import { pageStrings } from "@/lib/strings/pages";

const t = pageStrings.tour;

describe("TourVideo", () => {
  it("is a full-resolution player that waits for the reader", () => {
    const { container } = render(<TourVideo />);
    const video = container.querySelector("video");
    expect(video).not.toBeNull();
    expect(video).toHaveAttribute("controls");
    expect(video).toHaveAttribute("preload", "none");
    expect(video).toHaveAttribute("poster", TOUR_POSTER);
    expect(video).toHaveAttribute("aria-label", t.label);
    expect(video).toHaveAttribute("width", "1920");
    expect(video).toHaveAttribute("height", "1080");
    expect(video).not.toHaveAttribute("autoplay");
    expect(video?.querySelector("source")).toHaveAttribute("src", TOUR_VIDEO);
  });

  it("captions the player", () => {
    render(<TourVideo />);
    expect(screen.getByText(t.caption).tagName).toBe("FIGCAPTION");
  });
});
