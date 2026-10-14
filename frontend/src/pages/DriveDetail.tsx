import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Page, api, fmtCtc, fmtDate, fmtDateTime } from "../api";
import { FormModal } from "../components/FormModal";
import { Badge, DataTable, Field, KV, Notice } from "../components/ui";
import { useApi } from "../useApi";
import { Application, Department, DriveDetail as Detail, Skill, Student } from "../types";

const STATUSES = ["Upcoming", "Open", "Closed", "Completed", "Cancelled"];

export default function DriveDetail() {
  const { id } = useParams();
  const drive = useApi<Detail>(`/drives/${id}`);
  const departments = useApi<Department[]>("/departments");
  const skills = useApi<Skill[]>("/skills");
  const eligible = useApi<Page<Student> & { criteria_defined: boolean; department_restricted: boolean }>(
    `/drives/${id}/eligible-students?limit=200`,
  );
  const applications = useApi<Page<Application>>(`/applications?drive_id=${id}&limit=200`);

  const [tab, setTab] = useState<"setup" | "eligible" | "applications">("setup");
  const [editCriteria, setEditCriteria] = useState(false);
  const [addDept, setAddDept] = useState(false);
  const [addSkill, setAddSkill] = useState(false);
  const [flash, setFlash] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const d = drive.data;

  function reloadAll() {
    drive.reload();
    eligible.reload();
    applications.reload();
  }

  async function apply(studentId: number) {
    setErr(null);
    setFlash(null);
    try {
      await api.post("/applications", { student_id: studentId, drive_id: Number(id) });
      setFlash("Application submitted.");
      reloadAll();
    } catch (e) {
      const anyErr = e as { message?: string; reasons?: string[] };
      setErr([anyErr.message, ...(anyErr.reasons ?? [])].filter(Boolean).join(" "));
    }
  }

  async function setStatus(next: string) {
    setErr(null);
    try {
      await api.patch(`/drives/${id}`, { drive_status: next });
      setFlash(`Drive status changed to ${next}.`);
      reloadAll();
    } catch (e) {
      setErr((e as { message?: string }).message ?? "Could not change the status.");
    }
  }

  if (drive.loading && !d) return <div className="card"><div className="state">Loading drive…</div></div>;
  if (drive.error) return <Notice tone="error" title={drive.error} />;
  if (!d) return null;

  return (
    <>
      <div className="breadcrumb"><Link to="/drives">Job drives</Link> / {d.job_title}</div>
      <div className="page-head">
        <div>
          <h1>{d.job_title}</h1>
          <p>
            <Link to={`/companies/${d.company_id}`}>{d.company_name}</Link> · {fmtCtc(d.ctc_lpa)} ·{" "}
            <Badge value={d.drive_status} /> · {d.application_count} applications · {d.offer_count} offers
          </p>
        </div>
        <div className="row-actions">
          {STATUSES.filter((s) => s !== d.drive_status).map((s) => (
            <button key={s} onClick={() => setStatus(s)}>Set {s}</button>
          ))}
        </div>
      </div>

      {flash && <Notice tone="ok" title={flash} />}
      {err && <Notice tone="error" title={err} />}

      <div className="card">
        <h2>Drive details</h2>
        <div className="kv">
          <KV k="Job type" v={<Badge value={d.job_type} />} />
          <KV k="CTC" v={fmtCtc(d.ctc_lpa)} />
          <KV k="Openings" v={d.num_openings} />
          <KV k="Location" v={d.job_location} />
          <KV k="Application deadline" v={fmtDate(d.apply_deadline)} />
          <KV k="Drive date" v={fmtDate(d.drive_date)} />
        </div>
        {d.job_description && <p style={{ marginBottom: 0, fontSize: 13.5 }}>{d.job_description}</p>}
      </div>

      <div className="tabs" style={{ marginTop: 16 }}>
        <button aria-pressed={tab === "setup"} onClick={() => setTab("setup")}>Eligibility setup</button>
        <button aria-pressed={tab === "eligible"} onClick={() => setTab("eligible")}>
          Eligible students ({eligible.data?.total ?? 0})
        </button>
        <button aria-pressed={tab === "applications"} onClick={() => setTab("applications")}>
          Applications ({applications.data?.total ?? 0})
        </button>
      </div>

      {tab === "setup" && (
        <>
          <div className="card">
            <div className="page-head" style={{ marginBottom: 12 }}>
              <h2 style={{ margin: 0 }}>Eligibility criteria</h2>
              <button onClick={() => setEditCriteria(true)}>
                {d.eligibility_criteria ? "Edit criteria" : "Define criteria"}
              </button>
            </div>
            {d.eligibility_criteria ? (
              <div className="kv">
                <KV k="Minimum CGPA" v={Number(d.eligibility_criteria.min_cgpa).toFixed(2)} />
                <KV k="Maximum backlogs" v={d.eligibility_criteria.max_backlogs} />
                <KV k="Minimum 10th %" v={Number(d.eligibility_criteria.min_tenth_pct).toFixed(2)} />
                <KV k="Minimum 12th %" v={Number(d.eligibility_criteria.min_twelfth_pct).toFixed(2)} />
                <KV k="Eligible batch year" v={d.eligibility_criteria.eligible_batch_year} />
                <KV k="Placed students allowed" v={d.eligibility_criteria.allow_placed_students ? "Yes" : "No"} />
              </div>
            ) : (
              <Notice
                tone="info"
                title="This drive defines no eligibility criteria."
                reasons={[
                  "eligibility_criteria is an optional one-to-one record, so no row exists for this drive.",
                  "No academic gate is applied. This is not the same as all cut-offs being zero.",
                  "Department and deadline rules still apply.",
                ]}
              />
            )}
          </div>

          <div className="grid two" style={{ marginTop: 16 }}>
            <div className="card">
              <div className="page-head" style={{ marginBottom: 12 }}>
                <h2 style={{ margin: 0 }}>Eligible departments</h2>
                <button onClick={() => setAddDept(true)}>Add</button>
              </div>
              {d.eligible_departments.length === 0 && (
                <Notice tone="info" title="No department restriction, so every department may apply." />
              )}
              <DataTable
                rows={d.eligible_departments}
                rowKey={(r) => r.dept_id}
                empty="No department listed."
                columns={[
                  { header: "Code", cell: (r) => <Badge value={r.dept_code} /> },
                  { header: "Department", cell: (r) => r.dept_name },
                  {
                    header: "",
                    cell: (r) => (
                      <button className="link danger" onClick={async () => {
                        await api.del(`/drives/${id}/departments/${r.dept_id}`);
                        reloadAll();
                      }}>Remove</button>
                    ),
                  },
                ]}
              />
            </div>

            <div className="card">
              <div className="page-head" style={{ marginBottom: 12 }}>
                <h2 style={{ margin: 0 }}>Required skills</h2>
                <button onClick={() => setAddSkill(true)}>Add</button>
              </div>
              <DataTable
                rows={d.required_skills}
                rowKey={(r) => r.skill_id}
                empty="No skill requirement recorded."
                columns={[
                  { header: "Skill", cell: (r) => r.skill_name },
                  { header: "Mandatory", cell: (r) => <Badge value={r.is_mandatory ? "Yes" : "No"} /> },
                  { header: "Minimum level", cell: (r) => <Badge value={r.min_proficiency} /> },
                  {
                    header: "",
                    cell: (r) => (
                      <button className="link danger" onClick={async () => {
                        await api.del(`/drives/${id}/skills/${r.skill_id}`);
                        reloadAll();
                      }}>Remove</button>
                    ),
                  },
                ]}
              />
            </div>
          </div>
        </>
      )}

      {tab === "eligible" && (
        <div className="card">
          <h2>Students who satisfy this drive's rules</h2>
          <p style={{ fontSize: 13, color: "var(--text-muted)", marginTop: -6 }}>
            Evaluated in one SQL query. Students who already applied are excluded.
            {eligible.data && !eligible.data.criteria_defined && " This drive defines no academic criteria."}
          </p>
          <DataTable
            rows={eligible.data?.items}
            loading={eligible.loading}
            error={eligible.error}
            rowKey={(r) => r.student_id}
            empty="No student is currently eligible for this drive."
            columns={[
              { header: "Reg. no", cell: (r) => <Link className="mono" to={`/students/${r.student_id}`}>{r.reg_no}</Link> },
              { header: "Name", cell: (r) => [r.first_name, r.last_name].filter(Boolean).join(" ") },
              { header: "Department", cell: (r) => <Badge value={r.dept_code ?? "—"} /> },
              { header: "CGPA", num: true, cell: (r) => Number(r.cgpa).toFixed(2) },
              { header: "Backlogs", num: true, cell: (r) => r.active_backlogs },
              {
                header: "",
                cell: (r) => (
                  <div className="row-actions">
                    <Link to={`/drives/${id}/check/${r.student_id}`}>Why eligible</Link>
                    {d.drive_status === "Open" && (
                      <button className="link" onClick={() => apply(r.student_id)}>Apply</button>
                    )}
                  </div>
                ),
              },
            ]}
          />
        </div>
      )}

      {tab === "applications" && (
        <div className="card">
          <h2>Applications for this drive</h2>
          <DataTable
            rows={applications.data?.items}
            loading={applications.loading}
            error={applications.error}
            rowKey={(r) => r.application_id}
            empty="No application received for this drive."
            columns={[
              { header: "Reg. no", cell: (r) => <Link className="mono" to={`/students/${r.student_id}`}>{r.reg_no}</Link> },
              { header: "Student", cell: (r) => r.student_name },
              { header: "Applied", cell: (r) => fmtDateTime(r.applied_on) },
              { header: "Status", cell: (r) => <Badge value={r.application_status} /> },
              { header: "", cell: (r) => <Link to={`/applications/${r.application_id}`}>Open</Link> },
            ]}
          />
        </div>
      )}

      {editCriteria && (
        <FormModal
          title="Eligibility criteria"
          subtitle="Stored in eligibility_criteria, whose drive_id is both primary key and foreign key."
          submitLabel="Save criteria"
          onClose={() => setEditCriteria(false)}
          onSubmit={async (values) => {
            await api.put(`/drives/${id}/eligibility-criteria`, values);
            setFlash("Eligibility criteria saved.");
            reloadAll();
          }}
          fields={[
            { name: "min_cgpa", label: "Minimum CGPA", type: "number", step: "0.01", min: "0", max: "10",
              initial: d.eligibility_criteria?.min_cgpa ?? "0.00" },
            { name: "max_backlogs", label: "Maximum backlogs", type: "number", min: "0",
              initial: d.eligibility_criteria?.max_backlogs ?? 0 },
            { name: "min_tenth_pct", label: "Minimum 10th %", type: "number", step: "0.01", min: "0", max: "100",
              initial: d.eligibility_criteria?.min_tenth_pct ?? "0.00" },
            { name: "min_twelfth_pct", label: "Minimum 12th %", type: "number", step: "0.01", min: "0", max: "100",
              initial: d.eligibility_criteria?.min_twelfth_pct ?? "0.00" },
            { name: "eligible_batch_year", label: "Eligible batch year", type: "number", required: true, min: "2000", max: "2100",
              initial: d.eligibility_criteria?.eligible_batch_year ?? 2026 },
            { name: "allow_placed_students", label: "Allow already placed students", type: "checkbox",
              initial: d.eligibility_criteria?.allow_placed_students ?? false },
          ]}
        />
      )}

      {addDept && (
        <FormModal
          title="Add an eligible department"
          submitLabel="Add department"
          onClose={() => setAddDept(false)}
          onSubmit={async (values) => {
            await api.post(`/drives/${id}/departments/${values.dept_id}`, {});
            reloadAll();
          }}
          fields={[{
            name: "dept_id", label: "Department", type: "select", required: true, full: true,
            options: (departments.data ?? []).map((x) => ({ value: x.dept_id, label: `${x.dept_code} — ${x.dept_name}` })),
          }]}
        />
      )}

      {addSkill && (
        <FormModal
          title="Add a required skill"
          submitLabel="Add skill"
          onClose={() => setAddSkill(false)}
          onSubmit={async (values) => {
            await api.post(`/drives/${id}/skills`, values);
            reloadAll();
          }}
          fields={[
            {
              name: "skill_id", label: "Skill", type: "select", required: true, full: true,
              options: (skills.data ?? []).map((k) => ({ value: k.skill_id, label: `${k.skill_name} (${k.skill_category})` })),
            },
            { name: "min_proficiency", label: "Minimum level", type: "select", initial: "Beginner",
              options: ["Beginner", "Intermediate", "Advanced"].map((v) => ({ value: v, label: v })) },
            { name: "is_mandatory", label: "Mandatory", type: "checkbox", initial: true },
          ]}
        />
      )}
    </>
  );
}

/** The eligibility report for one student against one drive. */
export function EligibilityCheckPage() {
  const { id, studentId } = useParams();
  const check = useApi<import("../types").EligibilityCheck>(`/drives/${id}/eligibility/${studentId}`);
  const match = useApi<import("../types").SkillMatch>(`/drives/${id}/skill-match/${studentId}`);
  const c = check.data;

  if (check.loading && !c) return <div className="card"><div className="state">Running the eligibility check…</div></div>;
  if (check.error) return <Notice tone="error" title={check.error} />;
  if (!c) return null;

  return (
    <>
      <div className="breadcrumb"><Link to={`/drives/${id}`}>Drive {id}</Link> / eligibility check</div>
      <div className="page-head">
        <div>
          <h1>Eligibility check</h1>
          <p>Student {c.student_id} against drive {c.drive_id}.</p>
        </div>
      </div>

      {c.eligible
        ? <Notice tone="ok" title="This student is eligible to apply." />
        : <Notice tone="error" title="This student is not eligible to apply." reasons={c.reasons} />}

      <div className="card">
        <h2>Every rule checked</h2>
        <ul className="checklist">
          {c.checks.map((x) => (
            <li key={x.name} className={x.passed ? "pass" : "fail"}>
              <span className="mark">{x.passed ? "✓" : "✕"}</span>
              <span>
                <strong className="mono">{x.name}</strong> — required{" "}
                <span className="mono">{JSON.stringify(x.required)}</span>, actual{" "}
                <span className="mono">{JSON.stringify(x.actual)}</span>
              </span>
            </li>
          ))}
        </ul>
        {!c.criteria_defined && (
          <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 0 }}>
            This drive defines no eligibility_criteria row, so no academic gate applies. Missing
            criteria is reported, not read as zero cut-offs.
          </p>
        )}
      </div>

      {match.data && match.data.required_count > 0 && (
        <div className="card">
          <h2>Skill coverage</h2>
          <p style={{ fontSize: 13.5, marginTop: -4 }}>
            {match.data.matched_count} of {match.data.required_count} required skills met ·{" "}
            {match.data.mandatory_matched} of {match.data.mandatory_count} mandatory ·{" "}
            <Badge value={match.data.all_mandatory_met ? "Pass" : "Fail"} />
          </p>
          <DataTable
            rows={match.data.skills}
            rowKey={(r) => r.skill_id}
            empty="No skill requirement for this drive."
            columns={[
              { header: "Skill", cell: (r) => r.skill_name },
              { header: "Mandatory", cell: (r) => (r.is_mandatory ? "Yes" : "No") },
              { header: "Required level", cell: (r) => <Badge value={r.min_proficiency} /> },
              { header: "Student level", cell: (r) => (r.held ? <Badge value={r.proficiency_level} /> : <span style={{ color: "var(--text-muted)" }}>not held</span>) },
              { header: "Meets", cell: (r) => <Badge value={r.meets_proficiency ? "Pass" : "Fail"} /> },
            ]}
          />
        </div>
      )}
      <div className="card"><Field label="Note"><span style={{ fontSize: 13 }}>This page reads the same service-layer rules the API enforces on POST /applications.</span></Field></div>
    </>
  );
}
