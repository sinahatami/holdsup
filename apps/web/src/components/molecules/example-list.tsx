import { Sparkles, TextCursorInput } from "lucide-react";
import { useId } from "react";

/**
 * Ready-made claims as chips; picking one hands its text to the caller, which puts it in the
 * claim box. Each is a real button, so it takes Tab, Enter and Space. The chips wrap to as many
 * rows as the width needs, and the icon says "this goes into the box"; the name stays the claim.
 */
export function ExampleList({
  heading,
  examples,
  onPick,
}: {
  heading: string;
  examples: readonly string[];
  onPick: (example: string) => void;
}) {
  const headingId = useId();
  return (
    <div className="flex flex-col gap-3">
      <h2
        id={headingId}
        className="text-muted-foreground flex items-center gap-2 px-1 text-sm font-medium"
      >
        <Sparkles className="size-4" aria-hidden />
        {heading}
      </h2>
      <ul aria-labelledby={headingId} className="flex flex-wrap gap-2">
        {examples.map((ex) => (
          <li key={ex} className="max-w-full">
            <button
              type="button"
              className="group bg-popover text-foreground border-foreground/25 hover:border-foreground/60 hover:bg-accent focus-visible:outline-ring inline-flex min-h-10 max-w-full cursor-pointer items-center gap-2 rounded-full border px-3.5 py-2 text-start text-sm leading-5 shadow-xs transition focus-visible:outline-2 focus-visible:outline-offset-2 active:bg-accent/70"
              onClick={() => onPick(ex)}
            >
              <TextCursorInput
                className="text-muted-foreground group-hover:text-foreground size-4 shrink-0 transition"
                aria-hidden
              />
              {ex}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
