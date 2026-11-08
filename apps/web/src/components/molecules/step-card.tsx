/** One numbered step of "How it works". */
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
    <li className="glass flex flex-col gap-3 rounded-2xl p-5">
      <span className="bg-accent text-brand flex size-9 items-center justify-center rounded-xl font-bold tabular-nums">
        {number}
      </span>
      <h3 className="font-semibold">{title}</h3>
      <p className="text-muted-foreground text-sm leading-6">{body}</p>
    </li>
  );
}
