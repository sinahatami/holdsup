/**
 * Article links. The API decides what a link is (holdsup/page/guard.py); this
 * mirrors that rule so the form can say a page will be read before it is sent.
 */

const MAX_LINK = 2000;

/** The link when `text` is nothing but one web address, else null. A bare `www.` address is read as https. */
export function asLink(text: string): string | null {
  const s = text.trim();
  if (!s || s.length > MAX_LINK || /\s/.test(s)) return null;
  const lower = s.toLowerCase();
  if (lower.startsWith("http://") || lower.startsWith("https://")) return s;
  if (lower.startsWith("www.") && s.slice(4).includes("."))
    return `https://${s}`;
  return null;
}

/** The address when it is an http or https URL, so it is safe as a link's href; else null. */
export function webUrl(url: string): string | null {
  try {
    const { protocol } = new URL(url);
    return protocol === "http:" || protocol === "https:" ? url : null;
  } catch {
    return null;
  }
}

/** The site of an address without "www.": "news.example". The text as it came when it is not a URL. */
export function siteName(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "") || url;
  } catch {
    return url;
  }
}
