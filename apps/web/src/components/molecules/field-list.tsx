import type { ReactNode } from "react";

export interface Field {
  label: string;
  value: ReactNode;
  valueClassName?: string;
}

/** Label/value pairs, stacked on small screens and in two columns on wider ones. */
export function FieldList({ fields }: { fields: Field[] }) {
  return (
    <dl className="grid gap-x-4 gap-y-1 sm:grid-cols-[max-content_1fr]">
      {fields.map((f) => (
        <div key={f.label} className="contents">
          <dt className="text-muted-foreground font-medium">{f.label}</dt>
          <dd className={f.valueClassName}>{f.value}</dd>
        </div>
      ))}
    </dl>
  );
}
