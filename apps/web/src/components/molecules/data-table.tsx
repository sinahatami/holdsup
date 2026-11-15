import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export interface DataColumn {
  header: string;
  /** Numbers read best against the end edge. */
  align?: "start" | "end";
}

/**
 * A captioned table that scrolls sideways on a narrow screen without scrolling the page. The
 * region takes keyboard focus so the scroll is reachable without a mouse; the first cell of
 * each row is its header.
 */
export function DataTable({
  caption,
  columns,
  rows,
}: {
  caption: string;
  columns: DataColumn[];
  rows: { key: string; cells: ReactNode[] }[];
}) {
  const align = (c: DataColumn) =>
    c.align === "end" ? "text-end" : "text-start";
  return (
    <div
      role="region"
      aria-label={caption}
      tabIndex={0}
      className="glass focus-visible:ring-brand overflow-x-auto rounded-2xl outline-none [contain:inline-size] focus-visible:ring-2"
    >
      <table className="w-full text-sm">
        <caption className="text-muted-foreground p-4 text-start">
          {caption}
        </caption>
        <thead>
          <tr className="border-t">
            {columns.map((c) => (
              <th
                key={c.header}
                scope="col"
                className={cn("px-4 py-2 font-medium", align(c))}
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key} className="border-t align-top">
              {row.cells.map((cell, i) =>
                i === 0 ? (
                  <th
                    key={columns[i].header}
                    scope="row"
                    className="px-4 py-2 text-start font-medium"
                  >
                    {cell}
                  </th>
                ) : (
                  <td
                    key={columns[i].header}
                    className={cn("px-4 py-2 tabular-nums", align(columns[i]))}
                  >
                    {cell}
                  </td>
                ),
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
