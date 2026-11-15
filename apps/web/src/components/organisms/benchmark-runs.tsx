import { DataTable } from "@/components/molecules/data-table";
import type { BenchmarkRun } from "@/lib/api/client";
import { modelsText, rateText, runTitle, splitText } from "@/lib/benchmark";
import { strings } from "@/lib/strings";

const t = strings.benchmark;

/** Every run in the repository, pipeline and chatbot, so each model's own record is visible. */
export function BenchmarkRuns({ runs }: { runs: BenchmarkRun[] }) {
  return (
    <DataTable
      caption={t.runs.caption}
      columns={[
        { header: t.runs.columns.run },
        { header: t.runs.columns.split },
        { header: t.runs.columns.models },
        { header: t.runs.columns.accuracy, align: "end" },
        { header: t.runs.columns.leftOut, align: "end" },
        { header: t.runs.columns.calls, align: "end" },
        { header: t.runs.columns.seconds, align: "end" },
      ]}
      rows={runs.map((r) => ({
        key: r.name,
        cells: [
          runTitle(r),
          splitText(r.split),
          modelsText(r),
          rateText(r.accuracy),
          r.left_out,
          r.calls_per_claim ?? "—",
          r.seconds_per_claim ?? "—",
        ],
      }))}
    />
  );
}
