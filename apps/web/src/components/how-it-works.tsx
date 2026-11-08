import { strings } from "@/lib/strings";

export function HowItWorks() {
  return (
    <section
      id="how"
      aria-labelledby="how-heading"
      className="flex scroll-mt-24 flex-col gap-5"
    >
      <h2 id="how-heading" className="text-2xl font-bold tracking-tight">
        {strings.home.howHeading}
      </h2>
      <ol className="grid gap-4 sm:grid-cols-3">
        {strings.home.how.map((step, i) => (
          <li
            key={step.title}
            className="glass flex flex-col gap-3 rounded-2xl p-5"
          >
            <span className="bg-accent text-brand flex size-9 items-center justify-center rounded-xl font-bold tabular-nums">
              {i + 1}
            </span>
            <h3 className="font-semibold">{step.title}</h3>
            <p className="text-muted-foreground text-sm leading-6">
              {step.body}
            </p>
          </li>
        ))}
      </ol>
    </section>
  );
}
