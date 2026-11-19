"use client";

import { Check, Code, ImageDown, Link2, Share2, TextQuote } from "lucide-react";
import { pill } from "@/components/atoms/pill";
import { useShare } from "@/hooks/use-share";
import { embedCode } from "@/lib/embed";
import { strings } from "@/lib/strings";

const t = strings.share;

const MESSAGE = {
  link: t.linkCopied,
  summary: t.summaryCopied,
  embed: t.embedCopied,
  failed: t.failed,
} as const;

/**
 * Copy the link, copy a summary (the claim, its verdict and the link), copy the HTML that
 * puts the verdict on another site, download the check's card image, or open the device's
 * share sheet where there is one. The result is said in a status line, which is read out
 * as it appears.
 */
export function ShareActions({
  title,
  text,
  image,
  embed,
}: {
  /** The title for a shared link. */
  title: string;
  /** The claim and its verdict, without the link: the summary is this plus the link. */
  text: string;
  /** The check's card (the picture a shared link shows), to download. */
  image?: { href: string; name: string };
  /** The check to embed and how many claims it has (which sets the frame's height). */
  embed?: { id: string; claims: number };
}) {
  const { canShare, status, copyLink, copySummary, copyEmbed, share } =
    useShare(
      title,
      text,
      embed && ((origin) => embedCode({ origin, title, ...embed })),
    );
  return (
    <section aria-labelledby="share-heading" className="flex flex-col gap-2">
      <h2
        id="share-heading"
        className="text-muted-foreground text-sm font-medium"
      >
        {t.heading}
      </h2>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className={pill({ tone: "glass" })}
          onClick={copyLink}
        >
          <Link2 className="size-4" aria-hidden />
          {t.copyLink}
        </button>
        <button
          type="button"
          className={pill({ tone: "glass" })}
          onClick={copySummary}
        >
          <TextQuote className="size-4" aria-hidden />
          {t.copySummary}
        </button>
        {embed && (
          <button
            type="button"
            className={pill({ tone: "glass" })}
            onClick={copyEmbed}
          >
            <Code className="size-4" aria-hidden />
            {t.embed}
          </button>
        )}
        {image && (
          <a
            href={image.href}
            download={image.name}
            className={pill({ tone: "glass" })}
          >
            <ImageDown className="size-4" aria-hidden />
            {t.image}
          </a>
        )}
        {canShare && (
          <button
            type="button"
            className={pill({ tone: "glass" })}
            onClick={share}
          >
            <Share2 className="size-4" aria-hidden />
            {t.native}
          </button>
        )}
      </div>
      <p
        role="status"
        className="text-muted-foreground flex min-h-5 items-center gap-1.5 text-sm"
      >
        {status && (
          <>
            {status !== "failed" && <Check className="size-4" aria-hidden />}
            {MESSAGE[status]}
          </>
        )}
      </p>
    </section>
  );
}
