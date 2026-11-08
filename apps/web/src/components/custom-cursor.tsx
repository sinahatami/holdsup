"use client";

import { useEffect, useRef } from "react";

const INTERACTIVE = "a, button, summary, [role='radio'], [data-cursor='hover']";
const TEXT = "input, textarea, [contenteditable='true']";

/**
 * A dot that tracks the pointer exactly plus a ring that trails behind it.
 * Only active for fine pointers (mouse/trackpad) and when the user has not
 * asked for reduced motion; otherwise the native cursor is left untouched.
 */
export function CustomCursor() {
  const dot = useRef<HTMLDivElement>(null);
  const ring = useRef<HTMLDivElement>(null);

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
      rx += (x - rx) * 0.18;
      ry += (y - ry) * 0.18;
      dotEl.style.transform = `translate3d(${x}px, ${y}px, 0)`;
      ringEl.style.transform = `translate3d(${rx}px, ${ry}px, 0)`;
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);

    const onMove = (e: PointerEvent) => {
      x = e.clientX;
      y = e.clientY;
      const el = e.target instanceof Element ? e.target : null;
      const state = el?.closest(TEXT)
        ? "text"
        : el?.closest(INTERACTIVE)
          ? "link"
          : "idle";
      root.dataset.cursor = state;
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
  }, []);

  return (
    <div aria-hidden="true" className="pointer-events-none">
      <div ref={ring} className="cursor-ring">
        <span />
      </div>
      <div ref={dot} className="cursor-dot">
        <span />
      </div>
    </div>
  );
}
