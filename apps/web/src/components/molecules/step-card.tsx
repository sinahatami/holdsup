/** One numbered step of "How it works": a title and a single line. */
export function StepCard({
  number,
  title,
  body,
}: {
  number: number;
  title: string;
  body: string;
}) {
  return (
    <li className="flex gap-3">
      <span className="bg-accent text-brand flex size-8 shrink-0 items-center justify-center rounded-lg text-sm font-bold tabular-nums">
        {number}
      </span>
      <div className="flex flex-col gap-1">
        <h3 className="font-semibold">{title}</h3>
        <p className="text-muted-foreground text-sm leading-6">{body}</p>
      </div>
    </li>
  );
}
