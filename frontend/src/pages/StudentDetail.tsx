import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, fmtCtc, fmtDate, fmtDateTime } from "../api";
import { FormModal } from "../components/FormModal";
import { Badge, DataTable, KV, Notice } from "../components/ui";
import { useApi } from "../useApi";
import { Skill, StudentDetail as Detail } from "../types";

export default function StudentDetail() {
  const { id } = useParams();
  const student = useApi<Detail>(`/students/${id}`);
  const skills = useApi<Skill[]>("/skills");
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState(false);
  const [flash, setFlash] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const s = student.data;

  async function removeSkill(skillId: number) {
    setErr(null);
    try {
      await api.del(`/students/${id}/skills/${skillId}`);
      student.reload();
    } catch {
      setErr("Could not remove that skill.");
    }
  }

  if (student.loading && !s) return <div className="card"><div className="state">Loading student…</div></div>;
  if (student.error) return <Notice tone="error" title={student.error} />;
  if (!s) return null;

  return (
    <>
      <div className="breadcrumb"><Link to="/students">Students</Link> / {s.reg_no}</div>
      <div className="page-head">
        <div>
          <h1>{[s.first_name, s.last_name].filter(Boolean).join(" ")}</h1>
          <p>
            <span className="mono">{s.reg_no}</span> · {s.dept_name} · Batch {s.batch_year} ·{" "}
            <Badge value={s.is_placed ? "Placed" : "Not placed"} />
          </p>
        </div>
        <button onClick={() => setEditing(true)}>Edit details</button>
      </div>

      {flash && <Notice tone="ok" title={flash} />}
      {err && <Notice tone="error" title={err} />}

      <div className="card">
        <h2>Academic record</h2>
        <div className="kv">
          <KV k="CGPA" v={Number(s.cgpa).toFixed(2)} />
          <KV k="Active backlogs" v={s.active_backlogs} />
          <KV k="10th percentage" v={s.tenth_pct ? `${Number(s.tenth_pct).toFixed(2)}%` : "Not recorded"} />
          <KV k="12th percentage" v={s.twelfth_pct ? `${Number(s.twelfth_pct).toFixed(2)}%` : "Not recorded"} />
          <KV k="Email" v={s.email} />
          <KV k="Phone" v={s.phone} />
          <KV k="Date of birth" v={fmtDate(s.dob)} />
          <KV k="Gender" v={s.gender} />
          <KV k="Resume" v={s.resume_link ? <a href={s.resume_link} target="_blank" rel="noreferrer">Open resume</a> : "—"} />
        </div>
      </div>

      <div className="card">
        <div className="page-head" style={{ marginBottom: 12 }}>
          <h2 style={{ margin: 0 }}>Skills</h2>
          <button onClick={() => setAdding(true)}>Add skill</button>
        </div>
        <DataTable
          rows={s.skills}
          rowKey={(r) => r.skill_id}
          empty="No skill recorded for this student."
          columns={[
            { header: "Skill", cell: (r) => r.skill_name },
            { header: "Category", cell: (r) => <Badge value={r.skill_category} /> },
            { header: "Proficiency", cell: (r) => <Badge value={r.proficiency_level} /> },
            {
              header: "",
              cell: (r) => (
                <div className="row-actions">
                  <button className="link" onClick={async () => {
                    const next = r.proficiency_level === "Beginner" ? "Intermediate"
                      : r.proficiency_level === "Intermediate" ? "Advanced" : "Beginner";
                    await api.patch(`/students/${id}/skills/${r.skill_id}`, { proficiency_level: next });
                    student.reload();
                  }}>Change level</button>
                  <button className="link danger" onClick={() => removeSkill(r.skill_id)}>Remove</button>
                </div>
              ),
            },
          ]}
        />
      </div>

      <div className="card">
        <h2>Applications</h2>
        <DataTable
          rows={s.applications}
          rowKey={(r) => r.application_id}
          empty="This student has not applied to any drive."
          columns={[
            { header: "Company", cell: (r) => r.company_name },
            { header: "Role", cell: (r) => <Link to={`/applications/${r.application_id}`}>{r.job_title}</Link> },
            { header: "Applied", cell: (r) => fmtDateTime(r.applied_on) },
            { header: "Status", cell: (r) => <Badge value={r.application_status} /> },
            { header: "Rounds", num: true, cell: (r) => r.interview_rounds },
            { header: "Drive CTC", num: true, cell: (r) => fmtCtc(r.ctc_lpa) },
            {
              header: "Offer",
              cell: (r) => (r.offer_id ? <Badge value={r.offer_status} /> : <span style={{ color: "var(--text-muted)" }}>—</span>),
            },
            { header: "Offered CTC", num: true, cell: (r) => (r.offered_ctc_lpa ? fmtCtc(r.offered_ctc_lpa) : "—") },
          ]}
        />
      </div>

      {s.placement && (
        <div className="card">
          <h2>Verified placement</h2>
          <div className="kv">
            <KV k="Company" v={String(s.placement.company_name ?? "—")} />
            <KV k="Role" v={String(s.placement.role_title ?? "—")} />
            <KV k="Offered CTC" v={fmtCtc(s.placement.offered_ctc_lpa as string)} />
            <KV k="Academic year" v={String(s.placement.academic_year ?? "—")} />
            <KV k="Joined on" v={fmtDate(s.placement.actual_joining_date as string)} />
            <KV k="Employee code" v={String(s.placement.company_employee_code ?? "—")} />
            <KV k="Verified by" v={String(s.placement.verified_by ?? "—")} />
            <KV k="Verified on" v={fmtDate(s.placement.verified_on as string)} />
          </div>
        </div>
      )}

      {adding && (
        <FormModal
          title="Add a skill"
          subtitle="One row of student_skill, whose primary key is (student_id, skill_id)."
          submitLabel="Add skill"
          onClose={() => setAdding(false)}
          onSubmit={async (values) => {
            await api.post(`/students/${id}/skills`, values);
            setFlash("Skill added.");
            student.reload();
          }}
          fields={[
            {
              name: "skill_id", label: "Skill", type: "select", required: true,
              options: (skills.data ?? []).map((k) => ({ value: k.skill_id, label: `${k.skill_name} (${k.skill_category})` })),
            },
            {
              name: "proficiency_level", label: "Proficiency", type: "select", required: true, initial: "Beginner",
              options: ["Beginner", "Intermediate", "Advanced"].map((v) => ({ value: v, label: v })),
            },
          ]}
        />
      )}

      {editing && (
        <FormModal
          title="Edit student"
          submitLabel="Save changes"
          onClose={() => setEditing(false)}
          onSubmit={async (values) => {
            await api.patch(`/students/${id}`, values);
            setFlash("Student updated.");
            student.reload();
          }}
          fields={[
            { name: "first_name", label: "First name", initial: s.first_name },
            { name: "last_name", label: "Last name", initial: s.last_name ?? "" },
            { name: "email", label: "Email", type: "email", initial: s.email },
            { name: "phone", label: "Phone", initial: s.phone ?? "" },
            { name: "cgpa", label: "CGPA", type: "number", step: "0.01", min: "0", max: "10", initial: s.cgpa },
            { name: "active_backlogs", label: "Active backlogs", type: "number", min: "0", initial: s.active_backlogs },
            { name: "tenth_pct", label: "10th percentage", type: "number", step: "0.01", initial: s.tenth_pct ?? "" },
            { name: "twelfth_pct", label: "12th percentage", type: "number", step: "0.01", initial: s.twelfth_pct ?? "" },
            { name: "resume_link", label: "Resume link", full: true, initial: s.resume_link ?? "" },
          ]}
        />
      )}
    </>
  );
}
