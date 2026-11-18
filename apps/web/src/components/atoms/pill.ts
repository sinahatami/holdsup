import { cva, type VariantProps } from "class-variance-authority";

/**
 * The button look shared by buttons and links: a cut rectangle, solid blue for the one main
 * action, an ink outline for the rest. Apply it to whatever element fits (`<button>`,
 * `<Link>`, `<a>`): the style is the atom, the element keeps its own semantics.
 */
export const pill = cva(
  "inline-flex items-center gap-2 rounded-sm transition",
  {
    variants: {
      tone: {
        primary:
          // Enabled: solid blue, white text, the one saturated control. Off (native `disabled`
          // or `aria-disabled`): flat, faded and not-allowed, so it cannot pass for a live button.
          "bg-primary text-primary-foreground px-5 py-3 text-base font-semibold whitespace-nowrap sm:px-7 hover:brightness-110 " +
          "disabled:cursor-not-allowed disabled:bg-muted disabled:text-muted-foreground disabled:opacity-60 disabled:brightness-100 " +
          "aria-disabled:cursor-not-allowed aria-disabled:bg-muted aria-disabled:text-muted-foreground aria-disabled:opacity-60 aria-disabled:brightness-100",
        // An ink outline on paper: every other button and link that looks like one.
        glass:
          "bg-card border-foreground/80 hover:bg-accent border-[1.5px] px-4 py-2 text-sm font-medium",
      },
    },
    defaultVariants: { tone: "primary" },
  },
);

export type PillVariants = VariantProps<typeof pill>;
