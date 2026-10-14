import { ReactNode } from "react";

/** Status text to badge colour. Covers every ENUM in the Phase 1 schema. */
const TONE: Record<string, "ok" | "warn" | "bad" | "info" | "mute"> = {
  // drive_status
  Open: "ok", Upcoming: "info", Closed: "warn", Completed: "mute", Cancelled: "bad",
  // application_status
  Applied: "info", "Under Review": "warn", Shortlisted: "info",
  Selected: "ok", Rejected: "bad", Withdrawn: "mute",
  // interview result
  Pending: "warn", Pass: "ok", Fail: "bad", Absent: "mute",
  // offer_status
  Offered: "info", Accepted: "ok", Declined: "bad", Expired: "mute", Revoked: "bad",
  // proficiency
  Beginner: "mute", Intermediate: "info", Advanced: "ok",
  // interview mode
  Online: "info", Offline: "mute",
  // plain yes/no and connection state
  Yes: "ok", No: "mute", Placed: "ok", "Not placed": "mute",
  Connected: "ok", Unreachable: "bad",
};

export function Badge({ value }: { value: string | null | undefined }) {
  if (!value) return <span className="badge mute">—</span>;
  return <span className={`badge ${TONE[value] ?? "mute"}`}>{value}</span>;
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="stat">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {hint && <div className="hint">{hint}</div>}
    </div>
  );
}

export function KV({ k, v }: { k: string; v: ReactNode }) {
  return (
    <div>
      <div className="k">{k}</div>
      <div className="v">{v ?? "—"}</div>
    </div>
  );
}

export function Notice({
  tone = "info",
  title,
  reasons,
}: {
  tone?: "info" | "ok" | "error";
  title: string;
  reasons?: string[];
}) {
  return (
    <div className={`notice ${tone}`} role={tone === "error" ? "alert" : "status"}>
      <strong>{title}</strong>
      {reasons && reasons.length > 0 && (
        <ul>
          {reasons.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

export type Column<T> = {
  header: string;
  cell: (row: T) => ReactNode;
  num?: boolean;
};

export function DataTable<T>({
  columns,
  rows,
  loading,
  error,
  empty = "Nothing to show yet.",
  rowKey,
}: {
  columns: Column<T>[];
  rows: T[] | undefined | null;
  loading?: boolean;
  error?: string | null;
  empty?: string;
  rowKey: (row: T, index: number) => string | number;
}) {
  if (error) return <div className="table-wrap"><div className="state error">{error}</div></div>;
  if (loading && !rows) return <div className="table-wrap"><div className="state">Loading…</div></div>;
  if (!rows || rows.length === 0) return <div className="table-wrap"><div className="state">{empty}</div></div>;

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.header} className={c.num ? "num" : undefined}>
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={rowKey(row, i)}>
              {columns.map((c) => (
                <td key={c.header} className={c.num ? "num" : undefined}>
                  {c.cell(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Pager({
  total,
  limit,
  offset,
  onChange,
}: {
  total: number;
  limit: number;
  offset: number;
  onChange: (offset: number) => void;
}) {
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + limit, total);
  return (
    <div className="pager">
      <span>
        Showing {from}–{to} of {total}
      </span>
      <span className="spacer" />
      <button disabled={offset === 0} onClick={() => onChange(Math.max(0, offset - limit))}>
        Previous
      </button>
      <button disabled={to >= total} onClick={() => onChange(offset + limit)}>
        Next
      </button>
    </div>
  );
}

export function Field({
  label,
  children,
  wide,
  full,
}: {
  label: string;
  children: ReactNode;
  wide?: boolean;
  full?: boolean;
}) {
  return (
    <div className={`field${wide ? " wide" : ""}${full ? " full" : ""}`}>
      <label>{label}</label>
      {children}
    </div>
  );
}
