import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

// Atomic design: a layer may import only from layers below it
// (atoms < molecules < organisms < templates < app routes). lib/ and hooks/
// hold logic and never import components.
const LAYERS = ["atoms", "molecules", "organisms", "templates"];
const above = (layer) => LAYERS.slice(LAYERS.indexOf(layer) + 1);
const forbid = (files, groups, why) => ({
  files,
  rules: {
    "no-restricted-imports": [
      "error",
      { patterns: [{ group: groups, message: why }] },
    ],
  },
});
const layerRules = [
  ...LAYERS.slice(0, -1).map((layer) =>
    forbid(
      [`src/components/${layer}/**`],
      above(layer).flatMap((l) => [`@/components/${l}/*`, `../${l}/*`]),
      `${layer} may only import from lower layers (see src/components/README.md).`,
    ),
  ),
  forbid(
    ["src/lib/**", "src/hooks/**"],
    ["@/components/*", "@/components/**"],
    "lib/ and hooks/ hold logic only and must not import components.",
  ),
  forbid(
    ["src/lib/**"],
    ["@/hooks/*"],
    "lib/ is framework-free; hooks build on lib, not the other way round.",
  ),
];

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    "coverage/**",
  ]),
  ...layerRules,
]);

export default eslintConfig;
