import { routes } from "@/lib/routes";
import { strings } from "@/lib/strings";

/** How tall the frame is for one claim, and how much each further claim adds (CSS px). */
// A two-line claim with a long unit filled 391 px of 400 at 400 px wide (seen 2026-11-19).
const ONE_CLAIM_PX = 460;
const MORE_BASE_PX = 190;
const PER_CLAIM_PX = 150;
/** Taller than this and the widget scrolls inside its frame instead. */
const MAX_PX = 760;

/** The frame's height: enough for the widget at about 400 px wide, never taller than MAX_PX. */
export function embedHeight(claims: number): number {
  if (claims <= 1) return ONE_CLAIM_PX;
  return Math.min(MORE_BASE_PX + PER_CLAIM_PX * claims, MAX_PX);
}

/** Text made safe inside a double-quoted HTML attribute. */
export function escapeAttribute(text: string): string {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll('"', "&quot;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

/**
 * The HTML another site pastes to show a check's verdict: an iframe of /embed/[id] on this
 * origin, named for screen readers by the check's title. The verdict is drawn by HoldsUp on
 * each load, so the frame always shows what the check says now.
 */
export function embedCode({
  origin,
  id,
  title,
  claims,
}: {
  origin: string;
  id: string;
  title: string;
  claims: number;
}): string {
  const src = `${origin}${routes.embed(encodeURIComponent(id))}`;
  const name = strings.embed.frameTitle(title);
  return (
    `<iframe src="${escapeAttribute(src)}" title="${escapeAttribute(name)}" ` +
    `width="100%" height="${embedHeight(claims)}" ` +
    `style="border:0;max-width:640px" loading="lazy"></iframe>`
  );
}
