import { Fragment } from "react";

// A figure in running text (digits, with a separator only between digits so a full stop that
// ends the sentence stays out, then a per-cent sign or word), with the year it is about when
// one follows: "11.9% in 2015" is one mark, not two.
const FIGURE =
  /(\d+(?:[.,]\d+)*(?:\s?(?:%|per ?cent))?(?:\s(?:in|by|for|at)\s(?:1[89]|20)\d{2})?)/gi;

// A year on its own ("since 2008") is the period, not a figure, so it is not marked.
const LONE_YEAR = /^(?:1[89]|20)\d{2}$/;

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
        i % 2 === 1 && !LONE_YEAR.test(part) ? (
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
