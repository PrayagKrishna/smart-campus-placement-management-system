import { Link } from "react-router-dom";
import { fmtCtc } from "../api";
import { Badge, DataTable, Notice, Stat } from "../components/ui";
import { useApi } from "../useApi";
import { Dashboard as DashboardData, Health, ReportRun } from "../types";

export default function Dashboard() {
  const summary = useApi<DashboardData>("/dashboard");
  const health = useApi<Health>("/health");
  const funnel = useApi<ReportRun>("/reports/application-funnel");
  const t = summary.data?.totals;

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Placement Dashboard</h1>
          <p>Live totals from the MySQL database. Every figure is aggregated at read time.</p>
        </div>
      </div>

      {health.data && health.data.database !== "ok" && (
        <Notice tone="error" title="The API cannot reach the database." reasons={health.data.detail ? [health.data.detail] : []} />
      )}
      {summary.error && <Notice tone="error" title={summary.error} />}

      {summary.loading && !t && <div className="card"><div className="state">Loading totals…</div></div>}

      {t && (
        <>
          <div className="grid stats">
            <Stat label="Students" value={t.students} hint={`${t.departments} departments`} />
            <Stat label="Companies" value={t.companies} hint={`${t.job_drives} drives`} />
            <Stat label="Open drives" value={t.open_drives} hint="accepting applications" />
            <Stat label="Applications" value={t.applications} />
            <Stat label="Interviews" value={t.interviews} hint={`${t.interviews_pending} pending`} />
            <Stat label="Offers issued" value={t.offers_issued} hint={`${t.offers_accepted} accepted`} />
            <Stat label="Verified placements" value={t.verified_placements} hint={`${t.placement_percentage}% of students`} />
            <Stat
              label="Average accepted CTC"
              value={t.average_accepted_ctc_lpa === null ? "—" : fmtCtc(t.average_accepted_ctc_lpa)}
              hint={t.highest_offer_ctc_lpa === null ? undefined : `highest ${fmtCtc(t.highest_offer_ctc_lpa)}`}
            />
          </div>

          <div className="grid two" style={{ marginTop: 16 }}>
            <div className="card">
              <h2>Applications by status</h2>
              <DataTable
                rows={summary.data?.applications_by_status}
                rowKey={(r) => r.application_status}
                empty="No applications recorded."
                columns={[
                  { header: "Status", cell: (r) => <Badge value={r.application_status} /> },
                  { header: "Count", num: true, cell: (r) => r.count },
                  {
                    header: "Share",
                    cell: (r) => (
                      <div className="bar" title={`${((100 * r.count) / t.applications).toFixed(1)}%`}>
                        <span style={{ width: `${(100 * r.count) / Math.max(t.applications, 1)}%` }} />
                      </div>
                    ),
                  },
                ]}
              />
            </div>

            <div className="card">
              <h2>Offers by status</h2>
              <DataTable
                rows={summary.data?.offers_by_status}
                rowKey={(r) => r.offer_status}
                empty="No offers issued yet."
                columns={[
                  { header: "Status", cell: (r) => <Badge value={r.offer_status} /> },
                  { header: "Count", num: true, cell: (r) => r.count },
                ]}
              />
            </div>
          </div>

          <div className="card" style={{ marginTop: 16 }}>
            <h2>Placement pipeline</h2>
            <DataTable
              rows={funnel.data?.rows as { stage: string; count: number }[] | undefined}
              loading={funnel.loading}
              error={funnel.error}
              rowKey={(r) => r.stage}
              columns={[
                { header: "Stage", cell: (r) => r.stage },
                { header: "Count", num: true, cell: (r) => r.count },
                {
                  header: "Relative to applications",
                  cell: (r) => (
                    <div className="bar">
                      <span style={{ width: `${Math.min(100, (100 * r.count) / Math.max(t.applications, 1))}%` }} />
                    </div>
                  ),
                },
              ]}
            />
            <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 0 }}>
              Full breakdowns are on the <Link to="/reports">Reports</Link> page.
            </p>
          </div>

          {health.data && (
            <div className="card" style={{ marginTop: 16 }}>
              <h3>Database</h3>
              <p style={{ margin: 0, fontSize: 13.5, color: "var(--text-muted)" }}>
                <Badge value={health.data.database === "ok" ? "Connected" : "Unreachable"} />{" "}
                <span className="mono">{health.data.database_name}</span> on MySQL{" "}
                <span className="mono">{health.data.mysql_version}</span> · {health.data.table_count} tables
              </p>
            </div>
          )}
        </>
      )}
    </>
  );
}
