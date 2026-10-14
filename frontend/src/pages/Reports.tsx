import { useState } from "react";
import { Notice } from "../components/ui";
import { useApi } from "../useApi";
import { ReportMeta, ReportRun } from "../types";

/** Renders whatever columns a report returns, so adding a report needs no UI change. */
export default function Reports() {
  const reports = useApi<ReportMeta[]>("/reports");
  const [selected, setSelected] = useState<string | null>(null);
  const active = selected ?? reports.data?.[0]?.name ?? null;
  const run = useApi<ReportRun>(active ? `/reports/${active}?limit=500` : null, [active]);

  const columns = run.data?.rows.length ? Object.keys(run.data.rows[0]) : [];

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Reports</h1>
          <p>Relational queries over the live schema. Nothing here is a stored total.</p>
        </div>
      </div>

      {reports.error && <Notice tone="error" title={reports.error} />}

      <div className="tabs">
        {reports.data?.map((r) => (
          <button key={r.name} aria-pressed={r.name === active} onClick={() => setSelected(r.name)} title={r.description}>
            {r.name.replace(/-/g, " ")}
          </button>
        ))}
      </div>

      <div className="card">
        <h2>{active?.replace(/-/g, " ") ?? "Report"}</h2>
        <p style={{ fontSize: 13.5, color: "var(--text-muted)", marginTop: -6 }}>
          {run.data?.description ?? "Select a report."}
          {run.data && ` · ${run.data.row_count} rows`}
        </p>

        {run.error && <Notice tone="error" title={run.error} />}
        {run.loading && !run.data && <div className="state">Running the query…</div>}

        {run.data && run.data.rows.length === 0 && (
          <div className="state">This query returned no rows for the current data.</div>
        )}

        {run.data && run.data.rows.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  {columns.map((c) => (
                    <th key={c}>{c.replace(/_/g, " ")}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {run.data.rows.map((row, i) => (
                  <tr key={i}>
                    {columns.map((c) => {
                      const v = row[c];
                      const numeric = typeof v === "number" || (typeof v === "string" && v !== "" && !Number.isNaN(Number(v)));
                      return (
                        <td key={c} className={numeric ? "num" : undefined}>
                          {v === null || v === undefined ? "—" : String(v)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
