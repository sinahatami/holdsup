import { notFound } from "next/navigation";
import { BackLink } from "@/components/molecules/back-link";
import { ProblemAlert } from "@/components/molecules/problem-alert";
import { CheckResultView } from "@/components/organisms/check-result";
import { CheckTemplate } from "@/components/templates/check-template";
import { readCheck } from "@/lib/api/check";
import { CheckLive } from "./check-live";

/**
 * A check at its permanent link. One that has finished is drawn here, on the
 * server, from what the API stored: nothing is re-run, and the receipt is in
 * the page itself. One still running, or that the server could not read, goes
 * to the browser, which follows its live trace.
 */
export async function CheckPage({ id }: { id: string }) {
  const found = await readCheck(id);
  if (found.kind === "missing") notFound();
  if (found.kind === "unavailable") return <CheckLive id={id} />;

  const { result, error, status } = found.view;
  if (result) {
    return (
      <CheckTemplate actions={<BackLink />}>
        <CheckResultView result={result} />
      </CheckTemplate>
    );
  }
  if (status === "failed" && error) {
    return (
      <CheckTemplate actions={<BackLink />}>
        <ProblemAlert problem={error} />
      </CheckTemplate>
    );
  }
  return <CheckLive id={id} />;
}
