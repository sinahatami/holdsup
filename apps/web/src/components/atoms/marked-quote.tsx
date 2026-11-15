import { Fragment } from "react";

// A figure in running text: digits with any separators, and a trailing per-cent sign or word.
const FIGURE = /(\d[\d.,]*(?:\s?(?:%|per ?cent))?)/gi;

/**
 * The claim's words with each figure underlined in the editor's red pen. Only a visual mark:
 * the words read the same with or without it.
 */
export function MarkedQuote({ text }: { text: string }) {
  const parts = text.split(FIGURE);
  return (
    <>
      {parts.map((part, i) =>
        // split() with one capture group puts the matches at the odd places.
        i % 2 === 1 ? (
          <span key={i} className="pen-mark">
            {part}
          </span>
        ) : (
          <Fragment key={i}>{part}</Fragment>
        ),
      )}
    </>
  );
}
