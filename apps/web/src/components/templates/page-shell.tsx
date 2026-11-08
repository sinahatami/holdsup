import { cva, type VariantProps } from "class-variance-authority";
import type { ReactNode } from "react";

const shell = cva("mx-auto flex w-full flex-1 flex-col", {
  variants: {
    layout: {
      /** The landing page: roomy top and bottom. */
      home: "max-w-3xl gap-14 px-5 pt-16 pb-24 sm:px-6 sm:pt-24",
      /** A content page such as a check. */
      content: "max-w-3xl gap-8 px-5 py-12 sm:px-6 sm:py-16",
      /** A short centred message, such as 404. */
      message:
        "max-w-xl items-center justify-center gap-5 px-6 py-24 text-center",
    },
  },
  defaultVariants: { layout: "content" },
});

/** The page's <main> landmark: width, spacing and alignment for each kind of page. */
export function PageShell({
  layout,
  children,
}: VariantProps<typeof shell> & { children: ReactNode }) {
  return <main className={shell({ layout })}>{children}</main>;
}
