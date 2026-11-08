/**
 * The colour theme as an external store: "system" follows the OS, "light" and
 * "dark" are stored in localStorage and set as a class on <html>.
 */

export type Theme = "system" | "light" | "dark";

export const THEME_KEY = "holdsup-theme";

/** Runs before first paint (inlined in <head>) so a stored theme never flashes. */
export const themeInitScript = `try{var t=localStorage.getItem(${JSON.stringify(THEME_KEY)});if(t==="dark"||t==="light")document.documentElement.classList.add(t)}catch(e){}`;

const listeners = new Set<() => void>();

function read(): Theme {
  try {
    const v = localStorage.getItem(THEME_KEY);
    return v === "light" || v === "dark" ? v : "system";
  } catch {
    return "system";
  }
}

function apply(theme: Theme): void {
  const root = document.documentElement;
  root.classList.toggle("dark", theme === "dark");
  root.classList.toggle("light", theme === "light");
}

function set(theme: Theme): void {
  try {
    if (theme === "system") localStorage.removeItem(THEME_KEY);
    else localStorage.setItem(THEME_KEY, theme);
  } catch {}
  apply(theme);
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export const themeStore = {
  subscribe,
  set,
  getSnapshot: read,
  getServerSnapshot: (): Theme => "system",
};
