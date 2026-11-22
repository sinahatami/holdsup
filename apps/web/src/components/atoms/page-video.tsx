"use client";

import { type ComponentProps, useEffect, useRef } from "react";

/**
 * A `<video>` that stops when the reader leaves its page. With `cacheComponents` Next keeps a
 * page the reader navigated away from mounted but hidden (React `<Activity>`), so a playing
 * video would go on playing out of sight. Hiding runs effect cleanups, and so does unmounting:
 * both pause it here, and it waits at the same point when the reader comes back.
 */
export function PageVideo(props: ComponentProps<"video">) {
  const ref = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    const video = ref.current;
    return () => video?.pause();
  }, []);
  return <video ref={ref} {...props} />;
}
