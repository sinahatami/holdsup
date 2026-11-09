/** The old way to copy, for a page that is not a secure context or a browser without the async API. */
function copyWithSelection(text: string): boolean {
  const box = document.createElement("textarea");
  box.value = text;
  box.setAttribute("readonly", "");
  box.style.position = "fixed";
  box.style.opacity = "0";
  document.body.appendChild(box);
  box.select();
  try {
    return document.execCommand("copy");
  } catch {
    return false;
  } finally {
    box.remove();
  }
}

/**
 * Puts text on the clipboard; whether it worked. Call it straight from a click:
 * some browsers refuse a copy that comes after an `await`.
 */
export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // No async clipboard (an insecure page) or permission refused: try selecting.
    return copyWithSelection(text);
  }
}
