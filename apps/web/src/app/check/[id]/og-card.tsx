import type { CSSProperties } from "react";
import type { CheckResult, Label } from "@/lib/api/client";
import { shownLabel } from "@/lib/confidence";
import { sourceName } from "@/lib/format";
import { headlineFigure } from "@/lib/receipt";
import { clip, verdictLine } from "@/lib/receipt-meta";
import { strings } from "@/lib/strings";

// A picture cannot use the page's CSS variables or oklch(), so these are the dark theme's
// colours as sRGB. Every verdict pair is above 7:1.
const INK = {
  background: "#0b0d16",
  text: "#f0f1f9",
  muted: "#b1b6cb",
  brand: "#8b97ff",
};
const VERDICT: Record<Label, { fg: string; bg: string }> = {
  supported: { fg: "#65ebac", bg: "#0a3723" },
  supported_framing_matters: { fg: "#fbcd68", bg: "#3e2d04" },
  partly_supported: { fg: "#ffb678", bg: "#47270f" },
  not_supported: { fg: "#ffadad", bg: "#4e2021" },
  cant_check: { fg: "#c5cfdb", bg: "#272e38" },
};

// The image renderer lays out with flexbox only: every box that holds boxes says so.
const column: CSSProperties = { display: "flex", flexDirection: "column" };
const row: CSSProperties = { display: "flex", alignItems: "center" };

const frame: CSSProperties = {
  ...column,
  width: "100%",
  height: "100%",
  justifyContent: "space-between",
  padding: 64,
  background: INK.background,
  color: INK.text,
};

function Brand() {
  return (
    <div style={{ ...row, justifyContent: "space-between" }}>
      <div style={{ display: "flex", fontSize: 40, color: INK.brand }}>
        {strings.appName}
      </div>
      <div style={{ display: "flex", fontSize: 26, color: INK.muted }}>
        {strings.tagline}
      </div>
    </div>
  );
}

/** A claim's text is set smaller the longer it is, so it leaves room for what is under it. */
function quoteSize(text: string): number {
  if (text.length <= 80) return 56;
  if (text.length <= 140) return 46;
  return 38;
}

/** Two figures side by side must fit the picture: the longer they are, the smaller. */
function figureSize(claimed: string, official: string): number {
  const length = claimed.length + official.length;
  if (length <= 14) return 60;
  return length <= 24 ? 48 : 40;
}

function Figure({
  label,
  value,
  size,
}: {
  label: string;
  value: string;
  size: number;
}) {
  return (
    <div style={column}>
      <div style={{ display: "flex", fontSize: 26, color: INK.muted }}>
        {label}
      </div>
      <div style={{ display: "flex", fontSize: size }}>{value}</div>
    </div>
  );
}

/**
 * The picture of a finished check: the claim, how it came out in words and
 * colour, and for one claim the figure it states beside the official one.
 */
export function ReceiptCard({ result }: { result: CheckResult }) {
  const single = result.claims.length === 1;
  const [first] = result.claims;
  const tone = VERDICT[single ? shownLabel(first) : "cant_check"];
  const text = clip(single ? first.claim.quote : result.text, 200);
  const figure = single ? headlineFigure(first) : null;
  const size = figure ? figureSize(figure.claimed, figure.official) : 0;
  const source = single && first.data ? sourceName(first.data.source) : null;
  const verdict = single
    ? strings.verdicts[shownLabel(first)]
    : verdictLine(result.claims.map((c) => ({ label: shownLabel(c) })));
  return (
    <div style={frame}>
      <div style={{ ...column, gap: 32 }}>
        <Brand />
        <div style={{ display: "flex", fontSize: quoteSize(text) }}>
          {`“${text}”`}
        </div>
      </div>
      <div style={{ ...column, gap: 22 }}>
        {figure && (
          <div style={{ ...row, gap: 36 }}>
            <Figure
              label={strings.og.claimed}
              value={figure.claimed}
              size={size}
            />
            <div style={{ display: "flex", fontSize: 52, color: INK.muted }}>
              →
            </div>
            <Figure
              label={strings.og.official}
              value={figure.official}
              size={size}
            />
          </div>
        )}
        <div style={{ ...column, gap: 14 }}>
          <div
            style={{
              display: "flex",
              alignSelf: "flex-start",
              padding: "8px 26px",
              borderRadius: 999,
              fontSize: 34,
              color: tone.fg,
              background: tone.bg,
            }}
          >
            {verdict}
          </div>
          {source && (
            <div style={{ display: "flex", fontSize: 26, color: INK.muted }}>
              {strings.og.source(source)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/** What a link to a check that is missing, still running or unreadable shows: the brand alone. */
export function BrandCard() {
  return (
    <div style={{ ...frame, justifyContent: "center", gap: 24 }}>
      <div style={{ display: "flex", fontSize: 120, color: INK.brand }}>
        {strings.appName}
      </div>
      <div style={{ display: "flex", fontSize: 44, color: INK.text }}>
        {strings.tagline}
      </div>
      <div style={{ display: "flex", fontSize: 30, color: INK.muted }}>
        {strings.metaDescription}
      </div>
    </div>
  );
}
