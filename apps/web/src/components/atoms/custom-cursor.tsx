"use client";

import { useRef } from "react";
import { useCustomCursor } from "@/hooks/use-custom-cursor";

/** A dot that tracks the pointer exactly plus a ring that trails behind it. */
export function CustomCursor() {
  const dot = useRef<HTMLDivElement>(null);
  const ring = useRef<HTMLDivElement>(null);
  useCustomCursor(dot, ring);

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
