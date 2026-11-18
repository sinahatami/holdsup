import { renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useCustomCursor } from "@/hooks/use-custom-cursor";

const root = document.documentElement;
let frames: FrameRequestCallback[] = [];

/** A pointer that hovers (mouse or trackpad) unless `touch`, and motion unless `calm`. */
function pointer({ touch = false, calm = false } = {}) {
  vi.stubGlobal(
    "matchMedia",
    vi.fn((query: string) => ({
      matches: query.includes("reduced-motion") ? calm : !touch,
    })),
  );
}

function mount(dot: HTMLElement | null = document.createElement("div")) {
  const ring = document.createElement("div");
  const view = renderHook(() =>
    useCustomCursor({ current: dot }, { current: ring }),
  );
  return { ...view, dot, ring };
}

function move(target: Element, x: number, y: number) {
  target.dispatchEvent(
    new MouseEvent("pointermove", { clientX: x, clientY: y, bubbles: true }),
  );
}

/** Runs the animation frame the hook last asked for. */
function nextFrame() {
  const run = frames.pop();
  run?.(0);
}

beforeEach(() => {
  frames = [];
  vi.stubGlobal(
    "requestAnimationFrame",
    vi.fn((cb: FrameRequestCallback) => frames.push(cb)),
  );
  vi.stubGlobal("cancelAnimationFrame", vi.fn());
});

afterEach(() => {
  vi.unstubAllGlobals();
  document.body.replaceChildren();
});

describe("useCustomCursor", () => {
  it.each([
    ["a touch screen", { touch: true }],
    ["reduced motion", { calm: true }],
  ])("leaves the native cursor alone on %s", (_, media) => {
    pointer(media);
    mount();
    expect(root).not.toHaveClass("has-cursor");
    expect(requestAnimationFrame).not.toHaveBeenCalled();
  });

  it("does nothing before its elements exist", () => {
    pointer();
    mount(null);
    expect(root).not.toHaveClass("has-cursor");
  });

  it("puts the dot under the pointer and lets the ring trail behind", () => {
    pointer();
    const { dot, ring } = mount();
    expect(root).toHaveClass("has-cursor");

    move(document.body, 40, 30);
    nextFrame();

    expect(root).toHaveClass("cursor-on");
    expect(dot!.style.transform).toBe("translate3d(40px, 30px, 0px)");
    const [rx, ry] = ring.style.transform.match(/-?[\d.]+(?=px)/g)!.map(Number);
    expect(rx).toBeGreaterThan(-100);
    expect(rx).toBeLessThan(40);
    expect(ry).toBeGreaterThan(-100);
    expect(ry).toBeLessThan(30);
  });

  it("marks what is under the pointer: a link, a text field or nothing", () => {
    pointer();
    mount();
    const button = document.createElement("button");
    const input = document.createElement("input");
    document.body.append(button, input);

    move(button, 1, 1);
    expect(root.dataset.cursor).toBe("link");
    move(input, 1, 1);
    expect(root.dataset.cursor).toBe("text");
    move(document.body, 1, 1);
    expect(root.dataset.cursor).toBe("idle");
  });

  it("shows a press, and hides when the pointer leaves the page", () => {
    pointer();
    mount();
    move(document.body, 1, 1);

    window.dispatchEvent(new MouseEvent("pointerdown"));
    expect(root).toHaveClass("cursor-down");
    window.dispatchEvent(new MouseEvent("pointerup"));
    expect(root).not.toHaveClass("cursor-down");
    document.dispatchEvent(new MouseEvent("pointerleave"));
    expect(root).not.toHaveClass("cursor-on");
  });

  it("gives the native cursor back when unmounted", () => {
    pointer();
    const { unmount } = mount();
    move(document.body, 1, 1);

    unmount();

    expect(cancelAnimationFrame).toHaveBeenCalled();
    expect(root).not.toHaveClass("has-cursor");
    expect(root).not.toHaveClass("cursor-on");
    expect(root.dataset.cursor).toBeUndefined();
    move(document.body, 5, 5);
    expect(root.dataset.cursor).toBeUndefined();
  });
});
