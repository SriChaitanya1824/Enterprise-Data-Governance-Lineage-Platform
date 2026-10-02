import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../services/api";
import type { RecordData } from "../types";

export function Badge({ value }: { value: unknown }) {
  const text = String(value ?? "Unassigned");
  const tone = ["PASS", "Approved", "Closed", "Active", "Public"].includes(text)
    ? "good"
    : ["FAIL", "Critical", "High", "Open", "Rejected", "Unassigned"].includes(
          text,
        )
      ? "bad"
      : "neutral";
  return <span className={`badge ${tone}`}>{text}</span>;
}
export function State({
  loading,
  error,
}: {
  loading: boolean;
  error: Error | null;
}) {
  return loading ? (
    <div className="state">Loading governance records…</div>
  ) : error ? (
    <div className="error" role="alert">
      {error.message}
    </div>
  ) : null;
}
export function Heading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <div className="eyebrow">{eyebrow || "ENTERPRISE DATA OFFICE"}</div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}
export type Column = {
  key: string;
  label: string;
  render?: (row: RecordData) => React.ReactNode;
};
export function Table({
  rows,
  columns,
  link,
}: {
  rows: RecordData[];
  columns: Column[];
  link?: string;
}) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              {columns.map((c, i) => (
                <td key={c.key}>
                  {c.render ? (
                    c.render(row)
                  ) : i === 0 && link ? (
                    <Link to={`${link}/${row.id}`}>
                      {String(row[c.key] ?? "—")}
                    </Link>
                  ) : (
                    String(row[c.key] ?? "—")
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {!rows.length && (
        <div className="state">No records match your selection.</div>
      )}
    </div>
  );
}
export function Pager({
  page,
  total,
  size,
  onChange,
}: {
  page: number;
  total: number;
  size: number;
  onChange: (p: number) => void;
}) {
  return (
    <div className="pager">
      <span>
        {total} records · Page {page} of {Math.max(1, Math.ceil(total / size))}
      </span>
      <button disabled={page === 1} onClick={() => onChange(page - 1)}>
        Previous
      </button>
      <button
        disabled={page * size >= total}
        onClick={() => onChange(page + 1)}
      >
        Next
      </button>
    </div>
  );
}
export function RunButton({ path, label }: { path: string; label: string }) {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => api<Record<string, unknown>>(path, "POST", {}),
    onSuccess: () => client.invalidateQueries(),
  });
  return (
    <div>
      <button
        className="primary"
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending}
      >
        {mutation.isPending ? "Executing…" : label}
      </button>
      {mutation.isSuccess && (
        <span className="success"> Execution recorded</span>
      )}
      {mutation.error && <p className="error">{mutation.error.message}</p>}
    </div>
  );
}
export type FormField = {
  name: string;
  label: string;
  type?: string;
  options?: { value: string; label: string }[];
  required?: boolean;
};
export function Editor({
  title,
  fields,
  initial = {},
  onSave,
  onClose,
}: {
  title: string;
  fields: FormField[];
  initial?: Record<string, unknown>;
  onSave: (values: Record<string, unknown>) => Promise<unknown>;
  onClose: () => void;
}) {
  const [values, setValues] = useState<Record<string, unknown>>(initial);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <div className="modal-overlay">
      <section
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <h2>{title}</h2>
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy(true);
            try {
              await onSave(values);
              onClose();
            } catch (err) {
              setError((err as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          {fields.map((f) => (
            <label key={f.name}>
              {f.label}
              {f.options ? (
                <select
                  required={f.required}
                  value={String(values[f.name] ?? "")}
                  onChange={(e) =>
                    setValues({ ...values, [f.name]: e.target.value })
                  }
                >
                  <option value="">Select…</option>
                  {f.options.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              ) : f.type === "textarea" ? (
                <textarea
                  required={f.required}
                  value={String(values[f.name] ?? "")}
                  onChange={(e) =>
                    setValues({ ...values, [f.name]: e.target.value })
                  }
                />
              ) : (
                <input
                  required={f.required}
                  type={f.type || "text"}
                  value={String(values[f.name] ?? "")}
                  onChange={(e) =>
                    setValues({ ...values, [f.name]: e.target.value })
                  }
                />
              )}
            </label>
          ))}
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          <div className="form-actions">
            <button type="button" onClick={onClose}>
              Cancel
            </button>
            <button className="primary" disabled={busy}>
              {busy ? "Saving…" : "Save"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
