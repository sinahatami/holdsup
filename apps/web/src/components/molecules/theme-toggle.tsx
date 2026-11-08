"use client";

import { Monitor, Moon, Sun, type LucideIcon } from "lucide-react";
import { useTheme } from "@/hooks/use-theme";
import type { Theme } from "@/lib/theme";
import { strings } from "@/lib/strings";
import { cn } from "@/lib/utils";

const options: { value: Theme; label: string; Icon: LucideIcon }[] = [
  { value: "light", label: strings.nav.themeLight, Icon: Sun },
  { value: "system", label: strings.nav.themeSystem, Icon: Monitor },
  { value: "dark", label: strings.nav.themeDark, Icon: Moon },
];

export function ThemeToggle() {
  const [theme, setTheme] = useTheme();
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
          onClick={() => setTheme(value)}
          className={cn(
            "flex size-8 items-center justify-center rounded-full transition",
            theme === value
              ? "bg-primary text-primary-foreground shadow"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          <Icon className="size-4" aria-hidden />
        </button>
      ))}
    </div>
  );
}
