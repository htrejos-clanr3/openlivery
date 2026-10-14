"use client";

import type { ChangeEvent, ReactNode } from "react";

type Props = {
  label: ReactNode;
  hint?: ReactNode;
  checked?: boolean;
  defaultChecked?: boolean;
  onChange?: (checked: boolean) => void;
  name?: string;
  disabled?: boolean;
  required?: boolean;
  className?: string;
  title?: string;
};

/** Agency UI toggle: text on the left, pill switch on the right. */
export function SwitchRow({
  label,
  hint,
  checked,
  defaultChecked,
  onChange,
  name,
  disabled,
  required,
  className,
  title,
}: Props) {
  const controlled = typeof checked === "boolean";
  return (
    <label className={`switch-row${className ? ` ${className}` : ""}`} title={title}>
      <span>
        {typeof label === "string" || typeof label === "number" ? <strong>{label}</strong> : label}
        {hint ? <small>{hint}</small> : null}
      </span>
      <input
        type="checkbox"
        role="switch"
        name={name}
        disabled={disabled}
        required={required}
        aria-checked={controlled ? checked : undefined}
        {...(controlled
          ? {
              checked,
              onChange: (event: ChangeEvent<HTMLInputElement>) => onChange?.(event.target.checked),
            }
          : {
              defaultChecked,
              onChange: onChange
                ? (event: ChangeEvent<HTMLInputElement>) => onChange(event.target.checked)
                : undefined,
            })}
      />
    </label>
  );
}
