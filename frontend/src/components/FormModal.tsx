import { FormEvent, useState } from "react";
import { ApiError } from "../api";
import { Field, Notice } from "./ui";

export type FieldSpec = {
  name: string;
  label: string;
  type?: "text" | "number" | "date" | "datetime-local" | "email" | "textarea" | "select" | "checkbox";
  options?: { value: string | number; label: string }[];
  required?: boolean;
  full?: boolean;
  step?: string;
  min?: string;
  max?: string;
  placeholder?: string;
  help?: string;
  initial?: string | number | boolean;
};

/** One modal form, driven by a field spec, used by every create/edit screen. */
export function FormModal({
  title,
  subtitle,
  fields,
  submitLabel = "Save",
  onSubmit,
  onClose,
}: {
  title: string;
  subtitle?: string;
  fields: FieldSpec[];
  submitLabel?: string;
  onSubmit: (values: Record<string, unknown>) => Promise<void>;
  onClose: () => void;
}) {
  const [values, setValues] = useState<Record<string, string | boolean>>(() =>
    Object.fromEntries(
      fields.map((f) => [
        f.name,
        f.initial !== undefined ? (typeof f.initial === "boolean" ? f.initial : String(f.initial)) : f.type === "checkbox" ? false : "",
      ]),
    ),
  );
  const [error, setError] = useState<string | null>(null);
  const [reasons, setReasons] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setReasons([]);
    // Drop blanks so optional columns stay NULL rather than becoming "".
    const payload: Record<string, unknown> = {};
    for (const spec of fields) {
      const raw = values[spec.name];
      if (spec.type === "checkbox") {
        payload[spec.name] = Boolean(raw);
      } else if (raw !== "" && raw !== undefined) {
        payload[spec.name] = spec.type === "number" ? Number(raw) : raw;
      }
    }
    try {
      await onSubmit(payload);
      onClose();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
        setReasons(err.reasons);
      } else {
        setError("Could not reach the API.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="backdrop" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <form className="modal" onSubmit={submit}>
        <h2>{title}</h2>
        {subtitle && <p className="sub">{subtitle}</p>}
        {error && <Notice tone="error" title={error} reasons={reasons} />}
        <div className="modal-grid">
          {fields.map((f) => (
            <Field key={f.name} label={f.label + (f.required ? " *" : "")} full={f.full}>
              {f.type === "select" ? (
                <select
                  required={f.required}
                  value={String(values[f.name] ?? "")}
                  onChange={(e) => setValues((v) => ({ ...v, [f.name]: e.target.value }))}
                >
                  <option value="">{f.placeholder ?? "Select…"}</option>
                  {f.options?.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              ) : f.type === "textarea" ? (
                <textarea
                  required={f.required}
                  value={String(values[f.name] ?? "")}
                  onChange={(e) => setValues((v) => ({ ...v, [f.name]: e.target.value }))}
                />
              ) : f.type === "checkbox" ? (
                <input
                  type="checkbox"
                  style={{ width: 18, height: 18, minWidth: 18 }}
                  checked={Boolean(values[f.name])}
                  onChange={(e) => setValues((v) => ({ ...v, [f.name]: e.target.checked }))}
                />
              ) : (
                <input
                  type={f.type ?? "text"}
                  required={f.required}
                  step={f.step}
                  min={f.min}
                  max={f.max}
                  placeholder={f.placeholder}
                  value={String(values[f.name] ?? "")}
                  onChange={(e) => setValues((v) => ({ ...v, [f.name]: e.target.value }))}
                />
              )}
              {f.help && <span style={{ fontSize: 11.5, color: "var(--text-muted)" }}>{f.help}</span>}
            </Field>
          ))}
        </div>
        <div className="modal-actions">
          <button type="button" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button type="submit" className="primary" disabled={busy}>
            {busy ? "Saving…" : submitLabel}
          </button>
        </div>
      </form>
    </div>
  );
}
