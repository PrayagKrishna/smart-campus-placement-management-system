import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Page, api, fmtCtc, fmtDate, fmtDateTime, qs } from "../api";
import { FormModal } from "../components/FormModal";
import { Badge, DataTable, Field, KV, Notice, Pager } from "../components/ui";
import { useApi } from "../useApi";
import { Application, ApplicationDetail as Detail, Department, Drive, Student } from "../types";

const LIMIT = 15;
const APP_STATUSES = ["Applied", "Under Review", "Shortlisted", "Rejected", "Selected", "Withdrawn"];
const ROUND_TYPES = ["Aptitude Test", "Technical Test", "Group Discussion", "Technical Interview", "HR Interview", "Managerial"];

export default function Applications() {
  const [status, setStatus] = useState("");
  const [dept, setDept] = useState("");
  const [offset, setOffset] = useState(0);
  const [creating, setCreating] = useState(false);
  const [flash, setFlash] = useState<string | null>(null);

  const departments = useApi<Department[]>("/departments");
  const openDrives = useApi<Page<Drive>>("/drives?drive_status=Open&limit=200");
  const students = useApi<Page<Student>>("/students?limit=200");
  const list = useApi<Page<Application>>(
    `/applications${qs({ application_status: status, dept_id: dept, limit: LIMIT, offset })}`,
  );

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Applications</h1>
          <p>
            The <span className="mono">application</span> table resolves the many-to-many link between
            students and drives. One application per student per drive.
          </p>
        </div>
        <button className="primary" onClick={() => setCreating(true)}>Submit application</button>
      </div>

      {flash && <Notice tone="ok" title={flash} />}

      <div className="filters">
        <Field label="Status">
          <select value={status} onChange={(e) => { setOffset(0); setStatus(e.target.value); }}>
            <option value="">All</option>
            {APP_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </Field>
        <Field label="Department">
          <select value={dept} onChange={(e) => { setOffset(0); setDept(e.target.value); }}>
            <option value="">All</option>
            {departments.data?.map((d) => <option key={d.dept_id} value={d.dept_id}>{d.dept_code}</option>)}
          </select>
        </Field>
      </div>

      <DataTable
        rows={list.data?.items}
        loading={list.loading}
        error={list.error}
        rowKey={(r) => r.application_id}
        empty="No application matches these filters."
        columns={[
          { header: "Reg. no", cell: (r) => <Link className="mono" to={`/students/${r.student_id}`}>{r.reg_no}</Link> },
          { header: "Student", cell: (r) => r.student_name },
          { header: "Company", cell: (r) => r.company_name },
          { header: "Role", cell: (r) => <Link to={`/drives/${r.drive_id}`}>{r.job_title}</Link> },
          { header: "Applied", cell: (r) => fmtDateTime(r.applied_on) },
          { header: "Status", cell: (r) => <Badge value={r.application_status} /> },
          { header: "", cell: (r) => <Link to={`/applications/${r.application_id}`}>Open</Link> },
        ]}
      />
      {list.data && <Pager total={list.data.total} limit={LIMIT} offset={offset} onChange={setOffset} />}

      {creating && (
        <FormModal
          title="Submit an application"
          subtitle="The backend checks the deadline, the department, the academic criteria and the placed-student policy before it writes anything."
          submitLabel="Submit"
          onClose={() => setCreating(false)}
          onSubmit={async (values) => {
            await api.post("/applications", { student_id: Number(values.student_id), drive_id: Number(values.drive_id) });
            setFlash("Application submitted.");
            list.reload();
          }}
          fields={[
            {
              name: "student_id", label: "Student", type: "select", required: true, full: true,
              options: (students.data?.items ?? []).map((s) => ({
                value: s.student_id, label: `${s.reg_no} — ${s.first_name} ${s.last_name ?? ""} (CGPA ${Number(s.cgpa).toFixed(2)})`,
              })),
            },
            {
              name: "drive_id", label: "Open drive", type: "select", required: true, full: true,
              options: (openDrives.data?.items ?? []).map((d) => ({
                value: d.drive_id, label: `${d.company_name} — ${d.job_title}`,
              })),
            },
          ]}
        />
      )}
    </>
  );
}

export function ApplicationDetail() {
  const { id } = useParams();
  const app = useApi<Detail>(`/applications/${id}`);
  const [addRound, setAddRound] = useState(false);
  const [makeOffer, setMakeOffer] = useState(false);
  const [verify, setVerify] = useState(false);
  const [editRound, setEditRound] = useState<number | null>(null);
  const [flash, setFlash] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const a = app.data;

  async function setStatus(next: string) {
    setErr(null);
    try {
      await api.patch(`/applications/${id}`, { application_status: next });
      setFlash(`Application status changed to ${next}.`);
      app.reload();
    } catch (e) {
      setErr((e as { message?: string }).message ?? "Could not change the status.");
    }
  }

  if (app.loading && !a) return <div className="card"><div className="state">Loading application…</div></div>;
  if (app.error) return <Notice tone="error" title={app.error} />;
  if (!a) return null;

  const nextRound = (a.interviews.at(-1)?.round_no ?? 0) + 1;
  const editing = a.interviews.find((r) => r.interview_id === editRound);

  return (
    <>
      <div className="breadcrumb"><Link to="/applications">Applications</Link> / #{a.application_id}</div>
      <div className="page-head">
        <div>
          <h1>{a.student_name} → {a.company_name}</h1>
          <p>
            <Link className="mono" to={`/students/${a.student_id}`}>{a.reg_no}</Link> ·{" "}
            <Link to={`/drives/${a.drive_id}`}>{a.job_title}</Link> · applied {fmtDateTime(a.applied_on)} ·{" "}
            <Badge value={a.application_status} />
          </p>
        </div>
        <div className="row-actions">
          {APP_STATUSES.filter((s) => s !== a.application_status).map((s) => (
            <button key={s} onClick={() => setStatus(s)}>{s}</button>
          ))}
        </div>
      </div>

      {flash && <Notice tone="ok" title={flash} />}
      {err && <Notice tone="error" title={err} />}

      <div className="card">
        <div className="page-head" style={{ marginBottom: 12 }}>
          <h2 style={{ margin: 0 }}>Interview rounds</h2>
          <button onClick={() => setAddRound(true)}>Schedule round {nextRound}</button>
        </div>
        <DataTable
          rows={a.interviews}
          rowKey={(r) => r.interview_id}
          empty="No interview round scheduled yet."
          columns={[
            { header: "Round", num: true, cell: (r) => r.round_no },
            { header: "Type", cell: (r) => r.round_type },
            { header: "Mode", cell: (r) => <Badge value={r.mode} /> },
            { header: "Scheduled", cell: (r) => fmtDateTime(r.scheduled_at) },
            { header: "Venue", cell: (r) => r.venue ?? "—" },
            { header: "Interviewer", cell: (r) => r.interviewer_name ?? "—" },
            { header: "Score", num: true, cell: (r) => (r.score === null ? "—" : `${Number(r.score).toFixed(0)} / ${Number(r.max_score ?? 0).toFixed(0)}`) },
            { header: "Result", cell: (r) => <Badge value={r.result} /> },
            { header: "", cell: (r) => <button className="link" onClick={() => setEditRound(r.interview_id)}>Record result</button> },
          ]}
        />
      </div>

      <div className="card">
        <div className="page-head" style={{ marginBottom: 12 }}>
          <h2 style={{ margin: 0 }}>Offer</h2>
          {!a.offer && <button onClick={() => setMakeOffer(true)}>Issue offer</button>}
        </div>
        {a.offer ? (
          <>
            <div className="kv">
              <KV k="Role" v={a.offer.role_title} />
              <KV k="Offered CTC" v={fmtCtc(a.offer.offered_ctc_lpa)} />
              <KV k="Offer date" v={fmtDate(a.offer.offer_date)} />
              <KV k="Expected joining" v={fmtDate(a.offer.expected_joining_date)} />
              <KV k="Location" v={a.offer.job_location} />
              <KV k="Status" v={<Badge value={a.offer.offer_status} />} />
            </div>
            <div className="row-actions" style={{ marginTop: 12 }}>
              {["Offered", "Accepted", "Declined", "Expired", "Revoked"]
                .filter((s) => s !== a.offer!.offer_status)
                .map((s) => (
                  <button key={s} onClick={async () => {
                    setErr(null);
                    try {
                      await api.patch(`/offers/${a.offer!.offer_id}`, { offer_status: s });
                      setFlash(`Offer marked ${s}.`);
                      app.reload();
                    } catch (e) {
                      setErr((e as { message?: string }).message ?? "Could not update the offer.");
                    }
                  }}>Mark {s}</button>
                ))}
            </div>
          </>
        ) : (
          <Notice tone="info" title="No offer issued for this application. At most one offer is allowed per application." />
        )}
      </div>

      <div className="card">
        <div className="page-head" style={{ marginBottom: 12 }}>
          <h2 style={{ margin: 0 }}>Verified placement</h2>
          {a.offer && !a.placement && a.offer.offer_status === "Accepted" && (
            <button onClick={() => setVerify(true)}>Record joining</button>
          )}
        </div>
        {a.placement ? (
          <div className="kv">
            <KV k="Academic year" v={a.placement.academic_year} />
            <KV k="Joined on" v={fmtDate(a.placement.actual_joining_date)} />
            <KV k="Employee code" v={a.placement.company_employee_code} />
            <KV k="Verified by" v={a.placement.verified_by} />
            <KV k="Verified on" v={fmtDate(a.placement.verified_on)} />
            <KV k="Remarks" v={a.placement.remarks} />
          </div>
        ) : (
          <Notice
            tone="info"
            title="No verified placement for this application."
            reasons={[
              a.offer?.offer_status === "Accepted"
                ? "The offer is accepted, so a joining can now be verified."
                : "A placement record can only be created against an offer whose status is Accepted. An accepted offer is still not a verified placement.",
            ]}
          />
        )}
      </div>

      {addRound && (
        <FormModal
          title={`Schedule interview round ${nextRound}`}
          subtitle="An offline round must name a venue, and the round number must be unique for this application."
          submitLabel="Schedule round"
          onClose={() => setAddRound(false)}
          onSubmit={async (values) => {
            await api.post("/interviews", { ...values, application_id: Number(id) });
            setFlash("Interview round scheduled.");
            app.reload();
          }}
          fields={[
            { name: "round_no", label: "Round number", type: "number", min: "1", required: true, initial: nextRound },
            { name: "round_type", label: "Round type", type: "select", required: true,
              options: ROUND_TYPES.map((v) => ({ value: v, label: v })) },
            { name: "mode", label: "Mode", type: "select", required: true, initial: "Offline",
              options: ["Offline", "Online"].map((v) => ({ value: v, label: v })) },
            { name: "scheduled_at", label: "Scheduled at", type: "datetime-local", required: true },
            { name: "venue", label: "Venue", help: "Required when the mode is Offline" },
            { name: "interviewer_name", label: "Interviewer" },
          ]}
        />
      )}

      {editing && (
        <FormModal
          title={`Record round ${editing.round_no} result`}
          subtitle="The score may not exceed the maximum score."
          submitLabel="Save result"
          onClose={() => setEditRound(null)}
          onSubmit={async (values) => {
            await api.patch(`/interviews/${editing.interview_id}`, values);
            setFlash("Interview result recorded.");
            app.reload();
          }}
          fields={[
            { name: "result", label: "Result", type: "select", required: true, initial: editing.result,
              options: ["Pending", "Pass", "Fail", "Absent"].map((v) => ({ value: v, label: v })) },
            { name: "score", label: "Score", type: "number", step: "0.01", min: "0", initial: editing.score ?? "" },
            { name: "max_score", label: "Maximum score", type: "number", step: "0.01", min: "0.01", initial: editing.max_score ?? "100" },
            { name: "interviewer_name", label: "Interviewer", initial: editing.interviewer_name ?? "" },
            { name: "venue", label: "Venue", initial: editing.venue ?? "" },
            { name: "feedback", label: "Feedback", type: "textarea", full: true, initial: editing.feedback ?? "" },
          ]}
        />
      )}

      {makeOffer && (
        <FormModal
          title="Issue an offer"
          subtitle="Creating the offer also moves the application to Selected, in the same transaction."
          submitLabel="Issue offer"
          onClose={() => setMakeOffer(false)}
          onSubmit={async (values) => {
            await api.post("/offers", { ...values, application_id: Number(id) });
            setFlash("Offer issued.");
            app.reload();
          }}
          fields={[
            { name: "role_title", label: "Role title", required: true, full: true, initial: a.job_title },
            { name: "offered_ctc_lpa", label: "Offered CTC (LPA)", type: "number", step: "0.01", min: "0.01", required: true, initial: a.ctc_lpa },
            { name: "offer_date", label: "Offer date", type: "date", required: true, initial: new Date().toISOString().slice(0, 10) },
            { name: "expected_joining_date", label: "Expected joining date", type: "date", help: "Cannot be before the offer date" },
            { name: "job_location", label: "Location" },
            { name: "offer_status", label: "Status", type: "select", initial: "Offered",
              options: ["Offered", "Accepted", "Declined", "Expired", "Revoked"].map((v) => ({ value: v, label: v })) },
          ]}
        />
      )}

      {verify && a.offer && (
        <FormModal
          title="Record a verified joining"
          subtitle="Allowed only because this offer is Accepted. Exactly one placement record per offer."
          submitLabel="Record placement"
          onClose={() => setVerify(false)}
          onSubmit={async (values) => {
            await api.post("/placements", { ...values, offer_id: a.offer!.offer_id });
            setFlash("Placement verified.");
            app.reload();
          }}
          fields={[
            { name: "academic_year", label: "Academic year", required: true, initial: "2026-2027", help: "Format YYYY-YYYY" },
            { name: "verified_by", label: "Verified by", required: true, initial: "Placement Cell" },
            { name: "actual_joining_date", label: "Actual joining date", type: "date",
              initial: a.offer.expected_joining_date ?? "" },
            { name: "company_employee_code", label: "Employee code" },
            { name: "remarks", label: "Remarks", type: "textarea", full: true },
          ]}
        />
      )}
    </>
  );
}
