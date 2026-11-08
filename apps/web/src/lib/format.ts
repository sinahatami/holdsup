/** A computed number as the receipt shows it: up to 10 significant digits, "—" when absent. */
export function formatNumber(n: number | null | undefined): string {
  return n === null || n === undefined
    ? "—"
    : String(Number(n.toPrecision(10)));
}

/** An operation call as code, e.g. `change(start="2015", end="2023")`. */
export function formatCall(op: string, args: Record<string, unknown>): string {
  const list = Object.entries(args)
    .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
    .join(", ");
  return `${op}(${list})`;
}
