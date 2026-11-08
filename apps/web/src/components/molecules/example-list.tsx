import { Sparkles } from "lucide-react";

/** Ready-made claims; picking one hands its text to the caller. */
export function ExampleList({
  heading,
  examples,
  onPick,
}: {
  heading: string;
  examples: readonly string[];
  onPick: (example: string) => void;
}) {
  return (
    <div className="flex flex-col gap-3">
      <h2 className="text-muted-foreground flex items-center gap-2 px-1 text-sm font-medium">
        <Sparkles className="text-brand size-4" aria-hidden />
        {heading}
      </h2>
      <ul className="flex flex-col gap-2">
        {examples.map((ex) => (
          <li key={ex}>
            <button
              type="button"
              className="glass hover:border-brand/60 hover:bg-accent w-full rounded-2xl px-4 py-3 text-start text-sm leading-6 transition hover:-translate-y-0.5"
              onClick={() => onPick(ex)}
            >
              {ex}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
