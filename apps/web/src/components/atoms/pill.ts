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
          "shine bg-primary text-primary-foreground px-5 py-3 text-base font-semibold whitespace-nowrap sm:px-7 shadow-lg shadow-(color:--brand)/30 hover:-translate-y-0.5 hover:brightness-110 active:translate-y-0 disabled:translate-y-0 disabled:cursor-not-allowed disabled:bg-muted disabled:text-muted-foreground disabled:shadow-none disabled:brightness-100",
        glass: "glass hover:bg-accent px-4 py-2 text-sm font-medium",
      },
    },
    defaultVariants: { tone: "primary" },
  },
);

export type PillVariants = VariantProps<typeof pill>;
