import { readFile } from "node:fs/promises";
import { join } from "node:path";

/**
 * The share pictures' typefaces, read once per server: Newsreader for the claim and the
 * figures (the logo's serif) and Inter for the labels and the verdict. Static cuts trimmed to
 * Latin, because the image renderer reads neither WOFF2 nor variable fonts. Both are under the
 * SIL Open Font License; the licences sit beside the files in assets/og.
 */
const FONTS = [
  {
    file: "Newsreader-Regular.ttf",
    name: "Newsreader",
    weight: 400,
    style: "normal",
  },
  {
    file: "Newsreader-Medium.ttf",
    name: "Newsreader",
    weight: 500,
    style: "normal",
  },
  {
    file: "Newsreader-Italic.ttf",
    name: "Newsreader",
    weight: 400,
    style: "italic",
  },
  { file: "Inter-SemiBold.ttf", name: "Inter", weight: 600, style: "normal" },
] as const;

export type OgFont = {
  name: string;
  data: ArrayBuffer;
  weight: (typeof FONTS)[number]["weight"];
  style: (typeof FONTS)[number]["style"];
};

let loading: Promise<OgFont[]> | undefined;

export function ogFonts(): Promise<OgFont[]> {
  loading ??= Promise.all(
    FONTS.map(async ({ file, ...font }) => {
      const bytes = await readFile(join(process.cwd(), "assets/og", file));
      const data = bytes.buffer.slice(
        bytes.byteOffset,
        bytes.byteOffset + bytes.byteLength,
      ) as ArrayBuffer;
      return { ...font, data };
    }),
  ).catch((error: unknown) => {
    loading = undefined; // try the disk again next time instead of caching the failure
    throw error;
  });
  return loading;
}
