import { strings } from "@/lib/strings";

const t = strings.methodology;

/** The steps of a check in order, each tagged with who does the work: code or a language model. */
export function MethodSteps() {
  return (
    <ol className="flex flex-col gap-3">
      {t.steps.map((step, i) => (
        <li
          key={step.title}
          className="glass flex flex-col gap-2 rounded-2xl p-5 sm:flex-row sm:gap-5"
        >
          <span
            aria-hidden
            className="bg-primary text-primary-foreground flex size-8 shrink-0 items-center justify-center rounded-full text-sm font-bold"
          >
            {i + 1}
          </span>
          <div className="flex flex-col gap-1.5">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <h3 className="font-semibold">{step.title}</h3>
              <span className="bg-muted text-muted-foreground rounded-full px-2.5 py-0.5 text-xs font-semibold">
                {t.by[step.by]}
              </span>
            </div>
            <p className="text-sm leading-6">{step.body}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}
