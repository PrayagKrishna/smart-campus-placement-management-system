import { useState } from "react";
import { Link } from "react-router-dom";
import { Page, fmtCtc, fmtDate, qs } from "../api";
import { Badge, DataTable, Field, Pager } from "../components/ui";
import { useApi } from "../useApi";
import { Department, Placement } from "../types";

const LIMIT = 20;

export default function Placements() {
  const [year, setYear] = useState("");
  const [dept, setDept] = useState("");
  const [batch, setBatch] = useState("");
  const [offset, setOffset] = useState(0);

  const departments = useApi<Department[]>("/departments");
  const list = useApi<Page<Placement>>(
    `/placements${qs({ academic_year: year, dept_id: dept, batch_year: batch, limit: LIMIT, offset })}`,
  );

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Verified Placements</h1>
          <p>
            Rows in <span className="mono">placement_record</span>. Each one is a joining confirmed
            against an accepted offer.
          </p>
        </div>
      </div>

      <div className="filters">
        <Field label="Academic year">
          <input value={year} placeholder="2026-2027"
            onChange={(e) => { setOffset(0); setYear(e.target.value); }} />
        </Field>
        <Field label="Department">
          <select value={dept} onChange={(e) => { setOffset(0); setDept(e.target.value); }}>
            <option value="">All</option>
            {departments.data?.map((d) => <option key={d.dept_id} value={d.dept_id}>{d.dept_code}</option>)}
          </select>
        </Field>
        <Field label="Batch year">
          <input type="number" min="2000" max="2100" value={batch} placeholder="Any"
            onChange={(e) => { setOffset(0); setBatch(e.target.value); }} />
        </Field>
      </div>

      <DataTable
        rows={list.data?.items}
        loading={list.loading}
        error={list.error}
        rowKey={(r) => r.placement_id}
        empty="No verified placement matches these filters."
        columns={[
          { header: "Reg. no", cell: (r) => <Link className="mono" to={`/students/${r.student_id}`}>{r.reg_no}</Link> },
          { header: "Student", cell: (r) => r.student_name },
          { header: "Department", cell: (r) => <Badge value={r.dept_code} /> },
          { header: "Batch", num: true, cell: (r) => r.batch_year },
          { header: "Company", cell: (r) => r.company_name },
          { header: "Role", cell: (r) => r.role_title },
          { header: "CTC", num: true, cell: (r) => fmtCtc(r.offered_ctc_lpa) },
          { header: "Joined on", cell: (r) => fmtDate(r.actual_joining_date) },
          { header: "Employee code", cell: (r) => <span className="mono">{r.company_employee_code ?? "—"}</span> },
          { header: "Academic year", cell: (r) => r.academic_year },
          { header: "Verified by", cell: (r) => r.verified_by },
        ]}
      />
      {list.data && <Pager total={list.data.total} limit={LIMIT} offset={offset} onChange={setOffset} />}
    </>
  );
}
