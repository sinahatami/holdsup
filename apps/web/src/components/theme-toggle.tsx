"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { useSyncExternalStore } from "react";
import { strings } from "@/lib/strings";

type Theme = "system" | "light" | "dark";
const KEY = "holdsup-theme";
const listeners = new Set<() => void>();

function read(): Theme {
  try {
    const v = localStorage.getItem(KEY);
    return v === "light" || v === "dark" ? v : "system";
  } catch {
    return "system";
  }
}

function apply(t: Theme) {
  const root = document.documentElement;
  root.classList.toggle("dark", t === "dark");
  root.classList.toggle("light", t === "light");
}

function set(t: Theme) {
  try {
    if (t === "system") localStorage.removeItem(KEY);
    else localStorage.setItem(KEY, t);
  } catch {}
  apply(t);
  listeners.forEach((l) => l());
}

const subscribe = (cb: () => void) => {
  listeners.add(cb);
  return () => listeners.delete(cb);
};

const options: { value: Theme; label: string; Icon: typeof Sun }[] = [
  { value: "light", label: strings.nav.themeLight, Icon: Sun },
  { value: "system", label: strings.nav.themeSystem, Icon: Monitor },
  { value: "dark", label: strings.nav.themeDark, Icon: Moon },
];

export function ThemeToggle() {
  const theme = useSyncExternalStore(subscribe, read, () => "system" as Theme);
  return (
    <div
      role="radiogroup"
      aria-label={strings.nav.theme}
      className="glass inline-flex rounded-full p-1"
    >
      {options.map(({ value, label, Icon }) => (
        <button
          key={value}
          type="button"
          role="radio"
          aria-checked={theme === value}
          aria-label={label}
          title={label}
          onClick={() => set(value)}
          className={`flex size-8 items-center justify-center rounded-full transition ${
            theme === value
              ? "bg-primary text-primary-foreground shadow"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Icon className="size-4" aria-hidden />
        </button>
      ))}
    </div>
  );
}
