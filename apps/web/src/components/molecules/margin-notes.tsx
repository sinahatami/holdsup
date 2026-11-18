/**
 * The editor's notes beside a claim, in pen: short, one per line, each ruled off at its start.
 * The receipt says each again in plain text ("What the verdict compared"), so the handwriting
 * is hidden from screen readers rather than read twice.
 */
export function MarginNotes({ notes }: { notes: string[] }) {
  if (notes.length === 0) return null;
  return (
    <ul aria-hidden className="pen flex flex-col gap-3 text-2xl lg:pt-3">
      {notes.map((note) => (
        <li key={note} className="border-pen border-s-2 ps-3">
          {note}
        </li>
      ))}
    </ul>
  );
}
