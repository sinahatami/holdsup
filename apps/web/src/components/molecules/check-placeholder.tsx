import { strings } from "@/lib/strings";

const bar = "bg-muted rounded-full";

/**
 * Stands in for a check while it loads: the shape of the progress panel (a check just sent
 * shows that panel next), in muted bars, so nothing jumps when it arrives. The bars are
 * decorative; the status line says it in words.
 */
export function CheckPlaceholder() {
  return (
    <div className="glass flex flex-col gap-4 rounded-3xl p-6">
      <p role="status" className="sr-only">
        {strings.check.loading}
      </p>
      <div
        aria-hidden
        className="flex flex-col gap-4 motion-safe:animate-pulse"
        data-testid="check-placeholder"
      >
        <span className={`${bar} h-3 w-20`} />
        <span className="grid gap-3 sm:grid-cols-5 sm:gap-2">
          {[0, 1, 2, 3, 4].map((i) => (
            <span
              key={i}
              className="flex items-center gap-3 sm:flex-col sm:items-start sm:gap-2"
            >
              <span className="border-border size-6 shrink-0 rounded-full border-2" />
              <span className={`${bar} h-3 w-28 sm:w-20`} />
            </span>
          ))}
        </span>
      </div>
    </div>
  );
}
