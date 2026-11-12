"use client";

import { ArrowRight, Loader2 } from "lucide-react";
import {
  useRef,
  useState,
  type ChangeEvent,
  type KeyboardEvent,
  type ReactNode,
  type SubmitEvent,
} from "react";
import { pill } from "@/components/atoms/pill";
import { CharCounter } from "@/components/molecules/char-counter";
import { ExampleList } from "@/components/molecules/example-list";
import { VoiceInput } from "@/components/molecules/voice-input";
import { useDictation } from "@/hooks/use-dictation";
import { useModifierKey } from "@/hooks/use-modifier-key";
import { useSubmitCheck } from "@/hooks/use-submit-check";
import { withSpoken } from "@/lib/speech";
import { strings } from "@/lib/strings";

const kbd =
  "bg-muted rounded-md border px-1.5 py-0.5 font-mono text-[0.6875rem] font-medium";

/**
 * The claim box, its submit button and the examples. `children` is a slot under
 * the box and above the examples: the home page puts the sample receipt there.
 * A receipt uses it to reword one claim: `initialText` fills the box, `examples` is
 * off, `label` names the box, and `idPrefix` keeps its ids apart from the home page's.
 */
export function CheckForm({
  children,
  initialText = "",
  examples = true,
  label,
  idPrefix = "claim",
}: {
  children?: ReactNode;
  initialText?: string;
  examples?: boolean;
  label?: string;
  idPrefix?: string;
}) {
  const BOX_ID = idPrefix;
  const ERROR_ID = `${idPrefix}-error`;
  const HINT_ID = `${idPrefix}-hint`;
  const LANG_ID = `${idPrefix}-english`;
  const [text, setText] = useState(initialText);
  const box = useRef<HTMLTextAreaElement>(null);
  const { submit, busy, error } = useSubmitCheck();
  const modifier = useModifierKey();
  const t = strings.home;
  const v = strings.voice;

  // Speech is added after what was already in the box when listening began.
  const typedBefore = useRef("");
  const voice = useDictation({
    lang: v.lang,
    onText: (spoken) => setText(withSpoken(typedBefore.current, spoken)),
  });

  const tooLong = text.length > t.maxChars;
  const empty = !text.trim();
  const spokenProblem = voice.problem ? v.problems[voice.problem] : null;
  const message = tooLong ? t.tooLong : (error ?? spokenProblem);

  function onSubmit(e: SubmitEvent<HTMLFormElement>) {
    e.preventDefault();
    // The button is aria-disabled, not disabled, so it can still be pressed: send the visitor to the box.
    if (empty) box.current?.focus();
    if (busy || empty || tooLong) return;
    voice.cancel();
    void submit(text.trim());
  }

  // Typing takes over from listening, so late words never overwrite what was typed.
  function onChange(e: ChangeEvent<HTMLTextAreaElement>) {
    voice.cancel();
    setText(e.target.value);
  }

  // An example fills the box the same way typing would, then puts the cursor there to edit or send.
  function onPickExample(example: string) {
    voice.cancel();
    setText(example);
    box.current?.focus();
  }

  function onVoiceToggle() {
    if (voice.listening) return voice.stop();
    typedBefore.current = text;
    voice.start();
  }

  // Cmd+Enter on a Mac, Ctrl+Enter elsewhere; either works on any device.
  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      e.currentTarget.form?.requestSubmit();
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-6">
      <div className="bg-popover border-border-strong focus-within:ring-ring/40 focus-within:border-ring flex flex-col gap-2 rounded-3xl border p-4 shadow-(--shadow-lift) transition focus-within:ring-4">
        <label
          htmlFor={BOX_ID}
          className="text-muted-foreground px-1 text-sm font-medium"
        >
          {label ?? t.inputLabel}
        </label>
        <p
          id={LANG_ID}
          className="text-muted-foreground -mt-1 px-1 text-sm leading-5"
        >
          {voice.supported ? t.helperVoice : t.helper}
        </p>
        <textarea
          ref={box}
          id={BOX_ID}
          value={text}
          onChange={onChange}
          onKeyDown={onKeyDown}
          placeholder={t.placeholder}
          rows={3}
          className="placeholder:text-muted-foreground/85 w-full resize-none bg-transparent px-1 text-lg leading-8 outline-none"
          aria-describedby={
            message
              ? `${LANG_ID} ${HINT_ID} ${ERROR_ID}`
              : `${LANG_ID} ${HINT_ID}`
          }
          aria-keyshortcuts="Control+Enter Meta+Enter"
        />
        <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
            {voice.supported && (
              <VoiceInput
                listening={voice.listening}
                onToggle={onVoiceToggle}
              />
            )}
            <CharCounter count={text.length} max={t.maxChars} />
          </div>
          <div className="ms-auto flex items-center gap-4">
            <span
              id={HINT_ID}
              className="text-muted-foreground hidden items-center gap-1 text-xs sm:flex"
            >
              <kbd className={kbd}>{modifier}</kbd>+
              <kbd className={kbd}>Enter</kbd>
              <span className="ms-1">{t.shortcut}</span>
            </span>
            <button
              type="submit"
              aria-disabled={busy || empty || tooLong}
              className={pill({ tone: "primary" })}
            >
              {busy ? t.submitting : t.submit}
              {busy ? (
                <Loader2 className="size-4 animate-spin" aria-hidden />
              ) : (
                <ArrowRight className="size-4 rtl:rotate-180" aria-hidden />
              )}
            </button>
          </div>
        </div>
        {voice.supported && (
          <p
            role="status"
            className="text-muted-foreground px-1 text-xs leading-5 empty:hidden"
          >
            {voice.listening
              ? `${v.listening} ${v.privacy}`
              : voice.heard && !voice.problem && v.review(t.submit)}
          </p>
        )}
      </div>
      {message && (
        <p
          id={ERROR_ID}
          role="alert"
          className="text-destructive px-2 text-sm font-medium"
        >
          {message}
        </p>
      )}
      {children}
      {examples && (
        <ExampleList
          heading={t.examplesHeading}
          examples={t.examples}
          onPick={onPickExample}
        />
      )}
    </form>
  );
}
