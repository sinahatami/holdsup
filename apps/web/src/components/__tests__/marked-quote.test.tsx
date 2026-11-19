import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MarkedQuote } from "@/components/atoms/marked-quote";

function marks(text: string) {
  const { container } = render(
    <p>
      <MarkedQuote text={text} />
    </p>,
  );
  return {
    text: container.textContent,
    marked: [...container.querySelectorAll(".pen-mark")].map(
      (el) => el.textContent,
    ),
  };
}

describe("MarkedQuote", () => {
  it("marks each figure together with the year it is about", () => {
    const text =
      "Italy's unemployment rate fell from 11.9% in 2015 to 7.7% in 2023.";
    expect(marks(text)).toEqual({
      text,
      marked: ["11.9% in 2015", "7.7% in 2023"],
    });
  });

  it("marks a figure with no year, and leaves a lone year alone", () => {
    expect(marks("Italy's public debt is 133% of GDP.").marked).toEqual([
      "133%",
    ]);
    expect(
      marks("Youth unemployment in Italy has risen every year since 2008.")
        .marked,
    ).toEqual([]);
    expect(
      marks("Italian workers' average net pay rose 4.6% between 2021 and 2023.")
        .marked,
    ).toEqual(["4.6%"]);
  });

  it("leaves the full stop that ends the sentence out of the mark", () => {
    expect(marks("The rate was 7.7.").marked).toEqual(["7.7"]);
  });

  it("keeps the words exactly as given", () => {
    const text = "Wages rose 2,5 per cent by 2024, says the report.";
    const { text: shown, marked } = marks(text);
    expect(shown).toBe(text);
    expect(marked).toEqual(["2,5 per cent by 2024"]);
  });
});
