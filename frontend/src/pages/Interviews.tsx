import { useState } from "react";
import { Link } from "react-router-dom";
import { Page, fmtDateTime, qs } from "../api";
import { Badge, DataTable, Field, Pager } from "../components/ui";
import { useApi } from "../useApi";
import { Interview } from "../types";

const LIMIT = 20;
const RESULTS = ["Pending", "Pass", "Fail", "Absent"];
const ROUND_TYPES = ["Aptitude Test", "Technical Test", "Group Discussion", "Technical Interview", "HR Interview", "Managerial"];

export default function Interviews() {
  const [result, setResult] = useState("");
  const [roundType, setRoundType] = useState("");
  const [offset, setOffset] = useState(0);
  const list = useApi<Page<Interview>>(`/interviews${qs({ result, round_type: roundType, limit: LIMIT, offset })}`);

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Interview Management</h1>
          <p>
            Every round across all applications. Rounds are scheduled and results recorded from the
            application page.
          </p>
        </div>
      </div>

      <div className="filters">
        <Field label="Result">
          <select value={result} onChange={(e) => { setOffset(0); setResult(e.target.value); }}>
            <option value="">All</option>
            {RESULTS.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </Field>
        <Field label="Round type">
          <select value={roundType} onChange={(e) => { setOffset(0); setRoundType(e.target.value); }}>
            <option value="">All</option>
            {ROUND_TYPES.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </Field>
      </div>

      <DataTable
        rows={list.data?.items}
        loading={list.loading}
        error={list.error}
        rowKey={(r) => r.interview_id}
        empty="No interview round matches these filters."
        columns={[
          { header: "Reg. no", cell: (r) => <span className="mono">{r.reg_no ?? "—"}</span> },
          { header: "Student", cell: (r) => r.student_name ?? "—" },
          { header: "Company", cell: (r) => r.company_name ?? "—" },
          { header: "Role", cell: (r) => r.job_title ?? "—" },
          { header: "Round", num: true, cell: (r) => r.round_no },
          { header: "Type", cell: (r) => r.round_type },
          { header: "Mode", cell: (r) => r.mode },
          { header: "Scheduled", cell: (r) => fmtDateTime(r.scheduled_at) },
          { header: "Score", num: true, cell: (r) => (r.score === null ? "—" : `${Number(r.score).toFixed(0)} / ${Number(r.max_score ?? 0).toFixed(0)}`) },
          { header: "Result", cell: (r) => <Badge value={r.result} /> },
          { header: "", cell: (r) => <Link to={`/applications/${r.application_id}`}>Open</Link> },
        ]}
      />
      {list.data && <Pager total={list.data.total} limit={LIMIT} offset={offset} onChange={setOffset} />}
    </>
  );
}
