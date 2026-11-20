// @vitest-environment node
import { readdirSync, readFileSync } from "node:fs";
import { dirname, join, normalize, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

/**
 * Which text reaches the browser. Every module a "use client" file imports, directly or not,
 * is in some browser bundle, so the import graph says what text the browser downloads.
 */
const SRC = normalize(join(dirname(fileURLToPath(import.meta.url)), "../.."));

function sourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory())
      return entry.name === "__tests__" ? [] : sourceFiles(path);
    return /\.tsx?$/.test(entry.name) && !/\.(test|d)\.tsx?$/.test(entry.name)
      ? [path]
      : [];
  });
}

const files = new Map(
  sourceFiles(SRC).map((path) => [path, readFileSync(path, "utf8")]),
);

function resolve(from: string, spec: string): string | undefined {
  const base = spec.startsWith("@/")
    ? join(SRC, spec.slice(2))
    : spec.startsWith(".")
      ? normalize(join(dirname(from), spec))
      : undefined;
  if (base === undefined) return undefined;
  return [".ts", ".tsx", "/index.ts", "/index.tsx"]
    .map((ending) => base + ending)
    .find((candidate) => files.has(candidate));
}

function importsOf(path: string): string[] {
  const specs = [
    ...(files.get(path) ?? "").matchAll(
      /(?:from\s+|import\s*\(?\s*)["']([^"']+)["']/g,
    ),
  ];
  return specs.flatMap(([, spec]) => resolve(path, spec) ?? []);
}

function reachable(roots: string[]): Set<string> {
  const seen = new Set(roots);
  const queue = [...roots];
  for (let path = queue.pop(); path !== undefined; path = queue.pop()) {
    for (const next of importsOf(path)) {
      if (!seen.has(next)) {
        seen.add(next);
        queue.push(next);
      }
    }
  }
  return seen;
}

const name = (path: string) => relative(SRC, path);
const clientRoots = [...files]
  .filter(([, text]) => /^\s*(\/\/[^\n]*\n\s*)*["']use client["']/.test(text))
  .map(([path]) => path);

describe("text in the browser's bundles", () => {
  it("finds the client components (the check is not vacuous)", () => {
    expect(clientRoots.length).toBeGreaterThan(10);
    expect([...reachable(clientRoots)].map(name)).toContain(
      "lib/strings/index.ts",
    );
  });

  it("never includes the server-only pages' text", () => {
    const inBrowser = [...reachable(clientRoots)].map(name);
    expect(inBrowser).not.toContain("lib/strings/pages.ts");
  });

  it("keeps the error pages off the full strings, which they would load a second time", () => {
    for (const page of ["app/global-error.tsx", "app/(site)/error.tsx"]) {
      expect([...reachable([join(SRC, page)])].map(name)).not.toContain(
        "lib/strings/index.ts",
      );
    }
  });
});
