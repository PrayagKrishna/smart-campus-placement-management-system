import { useState } from "react";
import { Link } from "react-router-dom";
import { Page, fmtCtc, fmtDate, qs } from "../api";
import { Badge, DataTable, Field, Notice, Pager } from "../components/ui";
import { useApi } from "../useApi";
import { Offer } from "../types";

const LIMIT = 20;
const STATUSES = ["Offered", "Accepted", "Declined", "Expired", "Revoked"];

export default function Offers() {
  const [status, setStatus] = useState("");
  const [unverified, setUnverified] = useState(false);
  const [offset, setOffset] = useState(0);
  const list = useApi<Page<Offer>>(
    `/offers${qs({ offer_status: status, unverified_only: unverified ? "true" : "", limit: LIMIT, offset })}`,
  );

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Offers</h1>
          <p>
            One offer per application, enforced by a UNIQUE constraint. An accepted offer is still
            not a verified placement.
          </p>
        </div>
      </div>

      <Notice
        tone="info"
        title="Offer and placement are different facts."
        reasons={["An offer records what the company proposed. A placement record is a verified joining, confirmed by a named verifier."]}
      />

      <div className="filters">
        <Field label="Status">
          <select value={status} onChange={(e) => { setOffset(0); setStatus(e.target.value); }}>
            <option value="">All</option>
            {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </Field>
        <Field label="Awaiting verification">
          <select value={unverified ? "true" : ""} onChange={(e) => { setOffset(0); setUnverified(e.target.value === "true"); }}>
            <option value="">All offers</option>
            <option value="true">Accepted but not verified</option>
          </select>
        </Field>
      </div>

      <DataTable
        rows={list.data?.items}
        loading={list.loading}
        error={list.error}
        rowKey={(r) => r.offer_id}
        empty="No offer matches these filters."
        columns={[
          { header: "Reg. no", cell: (r) => <Link className="mono" to={`/students/${r.student_id}`}>{r.reg_no}</Link> },
          { header: "Student", cell: (r) => r.student_name },
          { header: "Company", cell: (r) => r.company_name },
          { header: "Role", cell: (r) => r.role_title },
          { header: "Offered CTC", num: true, cell: (r) => fmtCtc(r.offered_ctc_lpa) },
          { header: "Offer date", cell: (r) => fmtDate(r.offer_date) },
          { header: "Expected joining", cell: (r) => fmtDate(r.expected_joining_date) },
          { header: "Status", cell: (r) => <Badge value={r.offer_status} /> },
          { header: "", cell: (r) => <Link to={`/applications/${r.application_id}`}>Open</Link> },
        ]}
      />
      {list.data && <Pager total={list.data.total} limit={LIMIT} offset={offset} onChange={setOffset} />}
    </>
  );
}
