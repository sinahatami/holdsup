import { DataTable } from "@/components/molecules/data-table";
import type { ModelReport } from "@/lib/api/client";

/** Each trained model's headline figures from its committed report, and what to keep in mind. */
export function ModelReports({ reports }: { reports: ModelReport[] }) {
  return (
    <div className="flex flex-col gap-8">
      {reports.map((r) => (
        <div key={r.id} className="flex flex-col gap-3">
          <h3 className="text-xl font-semibold">{r.title}</h3>
          <DataTable
            caption={r.title}
            columns={r.table.columns.map((header, i) => ({
              header,
              align: i === 0 ? "start" : "end",
            }))}
            rows={r.table.rows.map((cells, i) => ({
              key: `${r.id}-${i}`,
              cells,
            }))}
          />
          <ul className="text-muted-foreground flex list-disc flex-col gap-2 ps-6 text-sm leading-6">
            {r.notes.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
