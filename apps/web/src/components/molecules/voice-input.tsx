import { Mic } from "lucide-react";
import { fieldControl } from "@/components/atoms/field-control";
import { pill } from "@/components/atoms/pill";
import { strings } from "@/lib/strings";
import { cn } from "@/lib/utils";

/**
 * A button that starts and stops listening, and a menu of the languages HoldsUp offers to
 * listen for. Shown only where the browser can do speech recognition; the box fills itself.
 */
export function VoiceInput({
  listening,
  language,
  onLanguage,
  onToggle,
}: {
  listening: boolean;
  language: string;
  onLanguage: (code: string) => void;
  onToggle: () => void;
}) {
  const t = strings.voice;
  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={onToggle}
        className={cn(pill({ tone: "glass" }), "min-h-11 px-4")}
      >
        {listening ? (
          <span
            aria-hidden
            className="bg-destructive size-2.5 rounded-full motion-safe:animate-pulse"
          />
        ) : (
          <Mic className="size-4" aria-hidden />
        )}
        {listening ? t.stop : t.start}
      </button>
      <select
        aria-label={t.language}
        value={language}
        disabled={listening}
        onChange={(e) => onLanguage(e.target.value)}
        className={cn(fieldControl, "w-auto")}
      >
        {t.languages.map(({ code, label }) => (
          <option key={code} value={code}>
            {label}
          </option>
        ))}
      </select>
    </div>
  );
}
