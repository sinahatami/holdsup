"use client";

import {
  Check,
  Code,
  Copy,
  ImageDown,
  Link2,
  Share2,
  TextQuote,
  type LucideIcon,
} from "lucide-react";
import Image from "next/image";
import { useId, useRef, useState, type KeyboardEvent } from "react";
import { pill } from "@/components/atoms/pill";
import { useShare, type ShareStatus } from "@/hooks/use-share";
import { embedCode } from "@/lib/embed";
import { strings } from "@/lib/strings";
import { cn } from "@/lib/utils";

const t = strings.share;

type Way = "link" | "summary" | "embed" | "image";

const ICON: Record<Way, LucideIcon> = {
  link: Link2,
  summary: TextQuote,
  embed: Code,
  image: ImageDown,
};

const ACTION = {
  link: t.copyLink,
  summary: t.copySummary,
  embed: t.embed,
} as const;

const MESSAGE: Record<Exclude<ShareStatus, null>, string> = {
  link: t.linkCopied,
  summary: t.summaryCopied,
  embed: t.embedCopied,
  failed: t.failed,
};

/** The arrow that moves to the next tab: right, or left on a right-to-left page. */
function step(e: KeyboardEvent, dir: string): number {
  const next = dir === "rtl" ? "ArrowLeft" : "ArrowRight";
  const back = dir === "rtl" ? "ArrowRight" : "ArrowLeft";
  if (e.key === next) return 1;
  if (e.key === back) return -1;
  return 0;
}

/**
 * Ways to share a check, as tabs: the link, a summary (the claim, its verdict and the link),
 * HTML that puts the verdict on another page, and the check's card image. Each tab shows
 * exactly what it gives before anything is copied, says who it is for, and has one action.
 * The action's icon turns into a tick and a status line beside it says what was copied. If
 * the copy fails, the preview is selected so the reader can copy it by hand. Where the
 * device has a share sheet, a button opens it.
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
  const share = useShare(
    title,
    text,
    embed && ((origin) => embedCode({ origin, title, ...embed })),
  );
  const ways: Way[] = [
    "link",
    "summary",
    ...(embed ? (["embed"] as const) : []),
    ...(image ? (["image"] as const) : []),
  ];
  const [way, setWay] = useState<Way>("link");
  const id = useId();
  const tabs = useRef<(HTMLButtonElement | null)[]>([]);
  const preview = useRef<HTMLPreElement | null>(null);

  function choose(next: Way) {
    setWay(next);
    share.clearStatus();
  }

  function onTabKey(e: KeyboardEvent<HTMLDivElement>) {
    const at = ways.indexOf(way);
    let to = at + step(e, getComputedStyle(e.currentTarget).direction);
    if (e.key === "Home") to = 0;
    if (e.key === "End") to = ways.length - 1;
    if (to === at) return;
    e.preventDefault();
    to = (to + ways.length) % ways.length;
    choose(ways[to]);
    tabs.current[to]?.focus();
  }

  async function copy(what: Exclude<Way, "image">) {
    const ok = await share.copy(what);
    // Copying is refused (an old browser, a denied permission): hand the reader the text.
    if (!ok && preview.current) {
      window.getSelection()?.selectAllChildren(preview.current);
    }
  }

  const value =
    way === "link"
      ? share.url
      : way === "summary"
        ? share.summary
        : way === "embed"
          ? share.embedCode
          : null;
  const done = share.status !== null && share.status !== "failed";
  const ActionIcon = done ? Check : Copy;

  return (
    <section
      aria-labelledby="share-heading"
      className="glass flex flex-col gap-4 rounded-2xl p-4 sm:p-5"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="share-heading" className="text-sm font-medium">
          {t.heading}
        </h2>
        {share.canShare && (
          <button
            type="button"
            className={pill({ tone: "glass" })}
            onClick={share.share}
          >
            <Share2 className="size-4" aria-hidden />
            {t.native}
          </button>
        )}
      </div>

      <div
        role="tablist"
        aria-label={t.heading}
        onKeyDown={onTabKey}
        className="bg-muted/60 grid auto-cols-fr grid-flow-col gap-1 rounded-md p-1 sm:inline-flex sm:self-start"
      >
        {ways.map((w, i) => {
          const Icon = ICON[w];
          const selected = w === way;
          return (
            <button
              key={w}
              ref={(el) => {
                tabs.current[i] = el;
              }}
              type="button"
              role="tab"
              id={`${id}-tab-${w}`}
              aria-selected={selected}
              aria-controls={`${id}-panel`}
              tabIndex={selected ? 0 : -1}
              onClick={() => choose(w)}
              className={cn(
                "focus-visible:ring-ring flex items-center justify-center gap-1.5 rounded-sm px-2 py-1.5 sm:px-3 text-sm font-medium transition focus-visible:ring-2 focus-visible:outline-none",
                selected
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              <Icon className="hidden size-4 sm:block" aria-hidden />
              {t.tabs[w]}
            </button>
          );
        })}
      </div>

      <div
        role="tabpanel"
        id={`${id}-panel`}
        aria-labelledby={`${id}-tab-${way}`}
        className="flex flex-col gap-3"
      >
        {way === "image" && image ? (
          <Image
            src={image.href}
            alt={strings.og.alt}
            width={1200}
            height={630}
            unoptimized
            className="border-border h-auto w-full max-w-md rounded-md border"
          />
        ) : (
          <figure className="m-0 flex flex-col gap-1">
            <figcaption className="sr-only">{t.previewLabel}</figcaption>
            <pre
              ref={preview}
              data-testid="share-preview"
              className={cn(
                "bg-background/60 border-border max-h-40 min-h-11 overflow-auto rounded-md border px-3 py-2.5 text-sm leading-6 break-words whitespace-pre-wrap select-all",
                way === "summary" ? "font-sans" : "font-mono text-[0.8125rem]",
              )}
            >
              {value}
            </pre>
          </figure>
        )}
        <p className="text-muted-foreground text-sm leading-6">
          {t.hints[way]}
        </p>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          {way === "image" && image ? (
            <a
              href={image.href}
              download={image.name}
              className={pill({ tone: "glass" })}
            >
              <ImageDown className="size-4" aria-hidden />
              {t.image}
            </a>
          ) : (
            <button
              type="button"
              className={cn(
                pill({ tone: "glass" }),
                done && "border-brand text-brand",
              )}
              onClick={() => void copy(way as Exclude<Way, "image">)}
            >
              <ActionIcon className="size-4" aria-hidden />
              {ACTION[way as Exclude<Way, "image">]}
            </button>
          )}
          <p
            role="status"
            className={cn(
              "flex min-h-5 items-center text-sm",
              share.status === "failed"
                ? "text-foreground"
                : "text-muted-foreground",
            )}
          >
            {share.status && MESSAGE[share.status]}
          </p>
        </div>
      </div>
    </section>
  );
}
