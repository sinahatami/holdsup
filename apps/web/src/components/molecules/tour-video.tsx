import { PageVideo } from "@/components/atoms/page-video";
import { pageStrings } from "@/lib/strings/pages";

const t = pageStrings.tour;

/** Served from `public/video/`: the teaser's 1080p, 60 fps master, and its closing frame. */
export const TOUR_VIDEO = "/video/holdsup-teaser.mp4";
export const TOUR_POSTER = "/video/holdsup-teaser-poster.webp";

/**
 * The one-minute teaser, shown at the top of "How it works". It is narrated and its words are
 * on screen. It never plays by itself, fetches nothing but the poster until the reader presses
 * play (`preload="none"`), and stops when the reader moves to another page (`PageVideo`).
 */
export function TourVideo() {
  return (
    <figure className="flex flex-col gap-3">
      <PageVideo
        controls
        playsInline
        preload="none"
        poster={TOUR_POSTER}
        width={1920}
        height={1080}
        aria-label={t.label}
        className="glass block aspect-video h-auto w-full rounded-2xl"
      >
        <source src={TOUR_VIDEO} type="video/mp4" />
      </PageVideo>
      <figcaption className="text-muted-foreground text-sm">
        {t.caption}
      </figcaption>
    </figure>
  );
}
