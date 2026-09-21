import { useEffect, useState } from "react";

type NumericInputProps = Omit<React.InputHTMLAttributes<HTMLInputElement>, "value" | "onChange" | "onBlur"> & {
  value: number | null;
  onValueChange: (value: number | null) => void;
  commitEmpty?: boolean;
};

/** Keeps an editable numeric field blank while the user is replacing its value. */
export function NumericInput({ value, onValueChange, commitEmpty = true, ...props }: NumericInputProps) {
  const [draft, setDraft] = useState(value == null ? "" : String(value));
  const [focused, setFocused] = useState(false);

  useEffect(() => {
    if (!focused) setDraft(value == null ? "" : String(value));
  }, [focused, value]);

  return <input {...props} value={draft} onFocus={() => setFocused(true)} onChange={(event) => {
    const next = event.target.value;
    setDraft(next);
    if (next.trim() === "") {
      if (commitEmpty) onValueChange(null);
      return;
    }
    const parsed = Number(next);
    if (Number.isFinite(parsed)) onValueChange(parsed);
  }} onBlur={() => setFocused(false)} />;
}
