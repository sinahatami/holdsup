"use client";

import { useEffect, type RefObject } from "react";

const INTERACTIVE = "a, button, summary, [role='radio'], [data-cursor='hover']";
const TEXT = "input, textarea, [contenteditable='true']";
const TRAIL = 0.18; // share of the gap the ring closes each frame

type CursorState = "text" | "link" | "idle";

function stateAt(target: EventTarget | null): CursorState {
  const el = target instanceof Element ? target : null;
  if (el?.closest(TEXT)) return "text";
  if (el?.closest(INTERACTIVE)) return "link";
  return "idle";
}

/**
 * Moves `dot` with the pointer and lets `ring` trail behind it. Only for fine
 * pointers (mouse/trackpad) when the user has not asked for reduced motion;
 * otherwise the native cursor is left untouched.
 */
export function useCustomCursor(
  dot: RefObject<HTMLElement | null>,
  ring: RefObject<HTMLElement | null>,
): void {
  useEffect(() => {
    const fine = window.matchMedia("(hover: hover) and (pointer: fine)");
    const calm = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (!fine.matches || calm.matches) return;

    const root = document.documentElement;
    const dotEl = dot.current;
    const ringEl = ring.current;
    if (!dotEl || !ringEl) return;

    root.classList.add("has-cursor");
    let x = -100;
    let y = -100;
    let rx = x;
    let ry = y;
    let frame = 0;

    const tick = () => {
      rx += (x - rx) * TRAIL;
      ry += (y - ry) * TRAIL;
      dotEl.style.transform = `translate3d(${x}px, ${y}px, 0)`;
      ringEl.style.transform = `translate3d(${rx}px, ${ry}px, 0)`;
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);

    const onMove = (e: PointerEvent) => {
      x = e.clientX;
      y = e.clientY;
      root.dataset.cursor = stateAt(e.target);
      root.classList.add("cursor-on");
    };
    const onDown = () => root.classList.add("cursor-down");
    const onUp = () => root.classList.remove("cursor-down");
    const onLeave = () => root.classList.remove("cursor-on");

    window.addEventListener("pointermove", onMove, { passive: true });
    window.addEventListener("pointerdown", onDown);
    window.addEventListener("pointerup", onUp);
    document.addEventListener("pointerleave", onLeave);

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerdown", onDown);
      window.removeEventListener("pointerup", onUp);
      document.removeEventListener("pointerleave", onLeave);
      root.classList.remove("has-cursor", "cursor-on", "cursor-down");
      delete root.dataset.cursor;
    };
  }, [dot, ring]);
}
