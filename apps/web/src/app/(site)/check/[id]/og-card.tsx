import type { CSSProperties } from "react";
import type { CheckResult, Label } from "@/lib/api/client";
import { shownLabel } from "@/lib/confidence";
import { sourceName } from "@/lib/format";
import { LOGO_DOT, LOGO_INK, LOGO_VIEWBOX } from "@/lib/logo-art";
import { headlineFigure } from "@/lib/receipt";
import { clip, verdictLine } from "@/lib/receipt-meta";
import { strings } from "@/lib/strings";

// A picture cannot use the page's CSS variables or oklch(), so these are the light theme's
// colours as sRGB: ink on paper, and the record blue for the official figure and the logo's dot.
const INK = {
  paper: "#f6f2eb",
  text: "#13161c",
  muted: "#444850",
  rule: "#d4cdbf",
  brand: "#254bb2",
};
// The verdict stamps' colours (--v and --vbg in globals.css). Every pair is above 9:1.
const VERDICT: Record<Label, { fg: string; bg: string }> = {
  supported: { fg: "#00431b", bg: "#d3f9e3" },
  supported_framing_matters: { fg: "#572c00", bg: "#fff0c5" },
  partly_supported: { fg: "#6f1500", bg: "#ffe8d1" },
  not_supported: { fg: "#7f000b", bg: "#ffe6e5" },
  cant_check: { fg: "#242f3d", bg: "#eaeff5" },
};
// Families loaded by og-fonts.ts: the serif for words and figures, the sans for labels.
const SERIF = "Newsreader";
const SANS = "Inter";

// The image renderer lays out with flexbox only: every box that holds boxes says so.
const column: CSSProperties = { display: "flex", flexDirection: "column" };
const row: CSSProperties = { display: "flex", alignItems: "center" };

const frame: CSSProperties = {
  ...column,
  width: "100%",
  height: "100%",
  justifyContent: "space-between",
  padding: "52px 64px 56px",
  background: INK.paper,
  color: INK.text,
  fontFamily: SANS,
};

/** The logo, drawn from the same outlines as the site's. */
function Logo({ height }: { height: number }) {
  const [, , w, h] = LOGO_VIEWBOX.split(" ").map(Number);
  return (
    <svg
      width={(height * w) / h}
      height={height}
      viewBox={LOGO_VIEWBOX}
      role="img"
      aria-label={strings.appName}
    >
      <path d={LOGO_INK} fill={INK.text} />
      <circle
        cx={LOGO_DOT.cx}
        cy={LOGO_DOT.cy}
        r={LOGO_DOT.r}
        fill={INK.brand}
      />
    </svg>
  );
}

function Masthead() {
  return (
    <div
      style={{
        ...row,
        justifyContent: "space-between",
        paddingBottom: 24,
        borderBottom: `2px solid ${INK.rule}`,
      }}
    >
      <Logo height={46} />
      <div
        style={{
          display: "flex",
          fontFamily: SERIF,
          fontStyle: "italic",
          fontSize: 28,
          color: INK.muted,
        }}
      >
        {strings.tagline}
      </div>
    </div>
  );
}

/** A claim's text is set smaller the longer it is, so it leaves room for what is under it. */
function quoteSize(text: string): number {
  if (text.length <= 80) return 58;
  if (text.length <= 140) return 46;
  return 38;
}

/** Two figures side by side must fit the picture: the longer they are, the smaller. */
function figureSize(claimed: string, official: string): number {
  const length = claimed.length + official.length;
  if (length <= 14) return 60;
  return length <= 24 ? 48 : 40;
}

/** One side of "the claim, with its denominator": a label, the figure, a rule under it. */
function Figure({
  label,
  value,
  size,
  official = false,
}: {
  label: string;
  value: string;
  size: number;
  official?: boolean;
}) {
  const color = official ? INK.brand : INK.text;
  return (
    <div style={{ ...column, gap: 8 }}>
      <div
        style={{
          display: "flex",
          fontSize: 17,
          letterSpacing: 2.4,
          textTransform: "uppercase",
          color: official ? INK.brand : INK.muted,
        }}
      >
        {label}
      </div>
      <div
        style={{
          display: "flex",
          fontFamily: SERIF,
          fontWeight: 500,
          fontSize: size,
          lineHeight: 1.05,
          color,
        }}
      >
        {value}
      </div>
      <div
        style={{ display: "flex", height: 7, marginTop: 6, background: color }}
      />
    </div>
  );
}

/** The verdict as the site's rubber stamp: a double rule, capitals, a slight tilt. */
function Stamp({
  text,
  tone,
}: {
  text: string;
  tone: { fg: string; bg: string };
}) {
  return (
    <div
      style={{
        display: "flex",
        alignSelf: "flex-start",
        padding: 4,
        border: `4px solid ${tone.fg}`,
        background: tone.bg,
        transform: "rotate(-2deg)",
      }}
    >
      <div
        style={{
          display: "flex",
          padding: "10px 26px",
          border: `1.5px solid ${tone.fg}`,
          fontSize: 28,
          letterSpacing: 2.2,
          textTransform: "uppercase",
          color: tone.fg,
        }}
      >
        {text}
      </div>
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
      <div style={{ ...column, gap: 34 }}>
        <Masthead />
        <div
          style={{
            display: "flex",
            fontFamily: SERIF,
            fontSize: quoteSize(text),
            lineHeight: 1.16,
            letterSpacing: -0.4,
          }}
        >
          {`“${text}”`}
        </div>
      </div>
      <div
        style={{
          ...row,
          alignItems: "flex-end",
          justifyContent: "space-between",
          gap: 48,
        }}
      >
        <div style={{ ...column, gap: 18 }}>
          <Stamp text={verdict} tone={tone} />
          {source && (
            <div style={{ display: "flex", fontSize: 22, color: INK.muted }}>
              {strings.og.source(source)}
            </div>
          )}
        </div>
        {figure && (
          <div style={{ ...row, alignItems: "flex-end", gap: 44 }}>
            <Figure
              label={strings.og.claimed}
              value={figure.claimed}
              size={size}
            />
            <Figure
              label={strings.og.official}
              value={figure.official}
              size={size}
              official
            />
          </div>
        )}
      </div>
    </div>
  );
}

/** Two ruled margins, as on the site's printed pages. */
const rule = (edge: "top" | "bottom"): CSSProperties => ({
  position: "absolute",
  left: 64,
  right: 64,
  [edge]: 52,
  height: 2,
  background: INK.rule,
});

/**
 * The site's own picture, for any page without one and for a link to a check that is
 * missing, still running or unreadable: the logo over the tagline.
 */
export function BrandCard() {
  return (
    <div
      style={{
        ...frame,
        justifyContent: "center",
        alignItems: "center",
        position: "relative",
      }}
    >
      <div style={rule("top")} />
      <Logo height={146} />
      <div
        style={{
          display: "flex",
          marginTop: 44,
          fontFamily: SERIF,
          fontStyle: "italic",
          fontSize: 52,
          color: INK.text,
        }}
      >
        {strings.tagline}
      </div>
      <div
        style={{
          display: "flex",
          marginTop: 20,
          fontSize: 24,
          color: INK.muted,
        }}
      >
        {strings.metaDescription}
      </div>
      <div style={rule("bottom")} />
    </div>
  );
}
