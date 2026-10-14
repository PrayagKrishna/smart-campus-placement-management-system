import { useState } from "react";
import { Link } from "react-router-dom";
import { Page, api, qs } from "../api";
import { FormModal } from "../components/FormModal";
import { Badge, DataTable, Field, Notice, Pager } from "../components/ui";
import { useApi } from "../useApi";
import { Department, Student } from "../types";

const LIMIT = 15;

export default function Students() {
  const [q, setQ] = useState("");
  const [dept, setDept] = useState("");
  const [batch, setBatch] = useState("");
  const [minCgpa, setMinCgpa] = useState("");
  const [maxBacklogs, setMaxBacklogs] = useState("");
  const [placed, setPlaced] = useState("");
  const [offset, setOffset] = useState(0);
  const [creating, setCreating] = useState(false);
  const [flash, setFlash] = useState<string | null>(null);

  const departments = useApi<Department[]>("/departments");
  const path = `/students${qs({
    q, dept_id: dept, batch_year: batch, min_cgpa: minCgpa,
    max_backlogs: maxBacklogs, placed, limit: LIMIT, offset,
  })}`;
  const list = useApi<Page<Student>>(path);

  function reset<T>(setter: (v: T) => void) {
    return (value: T) => {
      setOffset(0);
      setter(value);
    };
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Students</h1>
          <p>Search, filter and register students. Backed by the <span className="mono">student</span> table.</p>
        </div>
        <button className="primary" onClick={() => setCreating(true)}>Register student</button>
      </div>

      {flash && <Notice tone="ok" title={flash} />}

      <div className="filters">
        <Field label="Search" wide>
          <input value={q} placeholder="Registration number, name or email"
            onChange={(e) => reset(setQ)(e.target.value)} />
        </Field>
        <Field label="Department">
          <select value={dept} onChange={(e) => reset(setDept)(e.target.value)}>
            <option value="">All</option>
            {departments.data?.map((d) => (
              <option key={d.dept_id} value={d.dept_id}>{d.dept_code}</option>
            ))}
          </select>
        </Field>
        <Field label="Batch year">
          <input type="number" min="2000" max="2100" value={batch} placeholder="Any"
            onChange={(e) => reset(setBatch)(e.target.value)} />
        </Field>
        <Field label="Min CGPA">
          <input type="number" step="0.01" min="0" max="10" value={minCgpa} placeholder="Any"
            onChange={(e) => reset(setMinCgpa)(e.target.value)} />
        </Field>
        <Field label="Max backlogs">
          <input type="number" min="0" value={maxBacklogs} placeholder="Any"
            onChange={(e) => reset(setMaxBacklogs)(e.target.value)} />
        </Field>
        <Field label="Placement">
          <select value={placed} onChange={(e) => reset(setPlaced)(e.target.value)}>
            <option value="">All</option>
            <option value="true">Placed</option>
            <option value="false">Not placed</option>
          </select>
        </Field>
      </div>

      <DataTable
        rows={list.data?.items}
        loading={list.loading}
        error={list.error}
        rowKey={(r) => r.student_id}
        empty="No student matches these filters."
        columns={[
          { header: "Reg. no", cell: (r) => <Link className="mono" to={`/students/${r.student_id}`}>{r.reg_no}</Link> },
          { header: "Name", cell: (r) => [r.first_name, r.last_name].filter(Boolean).join(" ") },
          { header: "Department", cell: (r) => <Badge value={r.dept_code ?? "—"} /> },
          { header: "Batch", num: true, cell: (r) => r.batch_year },
          { header: "CGPA", num: true, cell: (r) => Number(r.cgpa).toFixed(2) },
          { header: "Backlogs", num: true, cell: (r) => r.active_backlogs },
          { header: "Email", cell: (r) => <span style={{ fontSize: 12.5 }}>{r.email}</span> },
        ]}
      />
      {list.data && <Pager total={list.data.total} limit={LIMIT} offset={offset} onChange={setOffset} />}

      {creating && (
        <FormModal
          title="Register a student"
          subtitle="Validated against the same CHECK constraints the database enforces."
          submitLabel="Create student"
          onClose={() => setCreating(false)}
          onSubmit={async (values) => {
            const created = await api.post<Student>("/students", values);
            setFlash(`Registered ${created.reg_no}.`);
            list.reload();
          }}
          fields={[
            { name: "reg_no", label: "Registration number", required: true },
            { name: "first_name", label: "First name", required: true },
            { name: "last_name", label: "Last name" },
            { name: "email", label: "Email", type: "email", required: true },
            { name: "phone", label: "Phone", help: "Digits, spaces, + and - only" },
            { name: "dob", label: "Date of birth", type: "date" },
            { name: "gender", label: "Gender", type: "select", options: ["Male", "Female", "Other"].map((v) => ({ value: v, label: v })) },
            {
              name: "dept_id", label: "Department", type: "select", required: true,
              options: (departments.data ?? []).map((d) => ({ value: d.dept_id, label: `${d.dept_code} — ${d.dept_name}` })),
            },
            { name: "batch_year", label: "Batch year", type: "number", required: true, min: "2000", max: "2100", initial: 2026 },
            { name: "cgpa", label: "CGPA", type: "number", step: "0.01", min: "0", max: "10", initial: "0.00" },
            { name: "active_backlogs", label: "Active backlogs", type: "number", min: "0", initial: 0 },
            { name: "tenth_pct", label: "10th percentage", type: "number", step: "0.01", min: "0", max: "100" },
            { name: "twelfth_pct", label: "12th percentage", type: "number", step: "0.01", min: "0", max: "100" },
            { name: "resume_link", label: "Resume link", full: true },
          ]}
        />
      )}
    </>
  );
}
