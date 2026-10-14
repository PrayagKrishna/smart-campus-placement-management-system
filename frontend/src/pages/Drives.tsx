import { useState } from "react";
import { Link } from "react-router-dom";
import { Page, api, fmtCtc, fmtDate, qs } from "../api";
import { FormModal } from "../components/FormModal";
import { Badge, DataTable, Field, Notice, Pager } from "../components/ui";
import { useApi } from "../useApi";
import { Company, Department, Drive } from "../types";

const LIMIT = 15;
const STATUSES = ["Upcoming", "Open", "Closed", "Completed", "Cancelled"];
const JOB_TYPES = ["Internship", "Full Time", "Intern + FTE"];

export default function Drives() {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [jobType, setJobType] = useState("");
  const [dept, setDept] = useState("");
  const [minCtc, setMinCtc] = useState("");
  const [batch, setBatch] = useState("");
  const [offset, setOffset] = useState(0);
  const [creating, setCreating] = useState(false);
  const [flash, setFlash] = useState<string | null>(null);

  const departments = useApi<Department[]>("/departments");
  const companies = useApi<Page<Company>>("/companies?limit=200");
  const list = useApi<Page<Drive>>(
    `/drives${qs({ q, drive_status: status, job_type: jobType, dept_id: dept, min_ctc: minCtc, batch_year: batch, limit: LIMIT, offset })}`,
  );

  const change = <T,>(setter: (v: T) => void) => (value: T) => { setOffset(0); setter(value); };

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Job Drives</h1>
          <p>Recruitment drives, their eligibility setup and application counts.</p>
        </div>
        <button className="primary" onClick={() => setCreating(true)}>Create drive</button>
      </div>

      {flash && <Notice tone="ok" title={flash} />}

      <div className="filters">
        <Field label="Search" wide>
          <input value={q} placeholder="Role or company"
            onChange={(e) => change(setQ)(e.target.value)} />
        </Field>
        <Field label="Status">
          <select value={status} onChange={(e) => change(setStatus)(e.target.value)}>
            <option value="">All</option>
            {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </Field>
        <Field label="Job type">
          <select value={jobType} onChange={(e) => change(setJobType)(e.target.value)}>
            <option value="">All</option>
            {JOB_TYPES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </Field>
        <Field label="Eligible department">
          <select value={dept} onChange={(e) => change(setDept)(e.target.value)}>
            <option value="">All</option>
            {departments.data?.map((d) => <option key={d.dept_id} value={d.dept_id}>{d.dept_code}</option>)}
          </select>
        </Field>
        <Field label="Batch year">
          <input type="number" min="2000" max="2100" value={batch} placeholder="Any"
            onChange={(e) => change(setBatch)(e.target.value)} />
        </Field>
        <Field label="Min CTC (LPA)">
          <input type="number" step="0.5" min="0" value={minCtc} placeholder="Any"
            onChange={(e) => change(setMinCtc)(e.target.value)} />
        </Field>
      </div>

      <DataTable
        rows={list.data?.items}
        loading={list.loading}
        error={list.error}
        rowKey={(r) => r.drive_id}
        empty="No drive matches these filters."
        columns={[
          { header: "Company", cell: (r) => r.company_name },
          { header: "Role", cell: (r) => <Link to={`/drives/${r.drive_id}`}>{r.job_title}</Link> },
          { header: "Type", cell: (r) => <Badge value={r.job_type} /> },
          { header: "CTC", num: true, cell: (r) => fmtCtc(r.ctc_lpa) },
          { header: "Openings", num: true, cell: (r) => r.num_openings },
          { header: "Deadline", cell: (r) => fmtDate(r.apply_deadline) },
          { header: "Drive date", cell: (r) => fmtDate(r.drive_date) },
          { header: "Status", cell: (r) => <Badge value={r.drive_status} /> },
          { header: "Applications", num: true, cell: (r) => r.application_count ?? 0 },
        ]}
      />
      {list.data && <Pager total={list.data.total} limit={LIMIT} offset={offset} onChange={setOffset} />}

      {creating && (
        <FormModal
          title="Create a job drive"
          subtitle="The database requires the application deadline to be on or before the drive date."
          submitLabel="Create drive"
          onClose={() => setCreating(false)}
          onSubmit={async (values) => {
            const created = await api.post<Drive>("/drives", values);
            setFlash(`Created "${created.job_title}". Add eligibility criteria on the drive page.`);
            list.reload();
          }}
          fields={[
            {
              name: "company_id", label: "Company", type: "select", required: true, full: true,
              options: (companies.data?.items ?? []).map((c) => ({ value: c.company_id, label: c.company_name })),
            },
            { name: "job_title", label: "Job title", required: true, full: true },
            { name: "job_type", label: "Job type", type: "select", required: true, initial: "Full Time",
              options: JOB_TYPES.map((v) => ({ value: v, label: v })) },
            { name: "ctc_lpa", label: "CTC (LPA)", type: "number", step: "0.01", min: "0.01", required: true },
            { name: "job_location", label: "Location" },
            { name: "num_openings", label: "Openings", type: "number", min: "1", initial: 1 },
            { name: "apply_deadline", label: "Application deadline", type: "date", required: true },
            { name: "drive_date", label: "Drive date", type: "date", required: true },
            { name: "drive_status", label: "Status", type: "select", initial: "Upcoming",
              options: STATUSES.map((v) => ({ value: v, label: v })) },
            { name: "job_description", label: "Description", type: "textarea", full: true },
          ]}
        />
      )}
    </>
  );
}
