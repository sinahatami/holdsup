/** One numbered step of "How it works", with what that step produced in the sample receipt. */
export function StepCard({
  number,
  title,
  body,
  exampleLabel,
  example,
}: {
  number: number;
  title: string;
  body: string;
  exampleLabel: string;
  example: string;
}) {
  return (
    <li className="glass flex flex-col gap-3 rounded-2xl p-5">
      <span className="bg-accent text-brand flex size-9 items-center justify-center rounded-xl font-bold tabular-nums">
        {number}
      </span>
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="text-muted-foreground leading-7">{body}</p>
      <p className="bg-muted/60 mt-auto rounded-xl px-3 py-2 text-sm leading-6">
        <span className="text-muted-foreground block text-xs font-semibold tracking-wide uppercase">
          {exampleLabel}
        </span>
        {example}
      </p>
    </li>
  );
}
