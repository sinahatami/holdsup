import { cva, type VariantProps } from "class-variance-authority";

/**
 * The rounded "pill" look shared by buttons and links. Apply it to whatever
 * element fits (`<button>`, `<Link>`, `<a>`): the style is the atom, the
 * element keeps its own semantics.
 */
export const pill = cva(
  "inline-flex items-center gap-2 rounded-full transition",
  {
    variants: {
      tone: {
        primary:
          // Enabled: solid indigo, white text, the one saturated control. Off (native `disabled`
          // or `aria-disabled`): flat, faded and not-allowed, so it cannot pass for a live button.
          "shine bg-primary text-primary-foreground px-5 py-3 text-base font-semibold whitespace-nowrap sm:px-7 shadow-md shadow-(color:--brand)/25 motion-safe:hover:-translate-y-0.5 hover:brightness-110 active:translate-y-0 " +
          "disabled:translate-y-0 disabled:cursor-not-allowed disabled:bg-muted disabled:text-muted-foreground disabled:opacity-60 disabled:shadow-none disabled:brightness-100 " +
          "aria-disabled:translate-y-0 aria-disabled:cursor-not-allowed aria-disabled:bg-muted aria-disabled:text-muted-foreground aria-disabled:opacity-60 aria-disabled:shadow-none aria-disabled:brightness-100",
        glass: "glass hover:bg-accent px-4 py-2 text-sm font-medium",
      },
    },
    defaultVariants: { tone: "primary" },
  },
);

export type PillVariants = VariantProps<typeof pill>;
