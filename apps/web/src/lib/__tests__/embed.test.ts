import { describe, expect, it } from "vitest";
import { embedCode, embedHeight, escapeAttribute } from "@/lib/embed";

describe("embedHeight", () => {
  it("is one size for one claim and grows with each further claim, up to a cap", () => {
    expect(embedHeight(0)).toBe(embedHeight(1));
    expect(embedHeight(2)).toBeGreaterThan(embedHeight(1));
    expect(embedHeight(3)).toBeGreaterThan(embedHeight(2));
    expect(embedHeight(50)).toBe(embedHeight(60));
  });
});

describe("escapeAttribute", () => {
  it("leaves nothing that could close the attribute or open a tag", () => {
    expect(escapeAttribute(`a "b" <c> & 'd'`)).toBe(
      "a &quot;b&quot; &lt;c&gt; &amp; 'd'",
    );
  });

  it("escapes an ampersand once, before the entities it adds", () => {
    expect(escapeAttribute("&quot;")).toBe("&amp;quot;");
  });
});

describe("embedCode", () => {
  const base = {
    origin: "https://holdsup.example",
    id: "22222222-2222-4222-8222-222222222222",
    title: "Holds up · “Debt is 133% of GDP.”",
    claims: 1,
  };

  it("frames this site's embed page for the check, named for screen readers", () => {
    const code = embedCode(base);
    expect(code).toMatch(/^<iframe .*><\/iframe>$/);
    expect(code).toContain(
      'src="https://holdsup.example/embed/22222222-2222-4222-8222-222222222222"',
    );
    expect(code).toContain(
      'title="HoldsUp: Holds up · “Debt is 133% of GDP.”"',
    );
    expect(code).toContain(`height="${embedHeight(1)}"`);
    expect(code).toContain('loading="lazy"');
  });

  it("cannot be broken out of by quotes or tags in the claim", () => {
    const code = embedCode({
      ...base,
      title: `Not supported · “He said "45%" <script>alert(1)</script>”`,
    });
    expect(code).not.toContain("<script>");
    expect(code).toContain("&quot;45%&quot; &lt;script&gt;");
    // One element, opened once and closed once.
    expect(code.match(/<iframe /g)).toHaveLength(1);
    expect(code.match(/</g)).toHaveLength(2);
  });

  it("sizes the frame by the number of claims", () => {
    expect(embedCode({ ...base, claims: 3 })).toContain(
      `height="${embedHeight(3)}"`,
    );
  });

  it("keeps an odd id inside the path", () => {
    expect(embedCode({ ...base, id: "a/../b?c" })).toContain(
      'src="https://holdsup.example/embed/a%2F..%2Fb%3Fc"',
    );
  });
});
