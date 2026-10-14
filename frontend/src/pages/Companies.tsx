import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Page, api, fmtCtc, fmtDate, qs } from "../api";
import { FormModal } from "../components/FormModal";
import { Badge, DataTable, Field, KV, Notice, Pager } from "../components/ui";
import { useApi } from "../useApi";
import { Company, Drive } from "../types";

const LIMIT = 15;

const COMPANY_FIELDS = (c?: Company) => [
  { name: "company_name", label: "Company name", required: !c, full: true, initial: c?.company_name },
  { name: "industry", label: "Industry", initial: c?.industry ?? "" },
  { name: "city", label: "City", initial: c?.city ?? "" },
  { name: "hr_name", label: "HR contact name", required: !c, initial: c?.hr_name },
  { name: "hr_email", label: "HR email", type: "email" as const, required: !c, initial: c?.hr_email },
  { name: "hr_phone", label: "HR phone", initial: c?.hr_phone ?? "" },
  { name: "website", label: "Website", full: true, initial: c?.website ?? "" },
];

export default function Companies() {
  const [q, setQ] = useState("");
  const [offset, setOffset] = useState(0);
  const [creating, setCreating] = useState(false);
  const [flash, setFlash] = useState<string | null>(null);
  const list = useApi<Page<Company>>(`/companies${qs({ q, limit: LIMIT, offset })}`);

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Companies</h1>
          <p>Recruiters and their drives. <span className="mono">company_name</span> and <span className="mono">hr_email</span> are both unique.</p>
        </div>
        <button className="primary" onClick={() => setCreating(true)}>Add company</button>
      </div>

      {flash && <Notice tone="ok" title={flash} />}

      <div className="filters">
        <Field label="Search" wide>
          <input value={q} placeholder="Company name or industry"
            onChange={(e) => { setOffset(0); setQ(e.target.value); }} />
        </Field>
      </div>

      <DataTable
        rows={list.data?.items}
        loading={list.loading}
        error={list.error}
        rowKey={(r) => r.company_id}
        empty="No company matches that search."
        columns={[
          { header: "Company", cell: (r) => <Link to={`/companies/${r.company_id}`}>{r.company_name}</Link> },
          { header: "Industry", cell: (r) => r.industry ?? "—" },
          { header: "City", cell: (r) => r.city ?? "—" },
          { header: "HR contact", cell: (r) => r.hr_name },
          { header: "HR email", cell: (r) => <span style={{ fontSize: 12.5 }}>{r.hr_email}</span> },
          { header: "Drives", num: true, cell: (r) => r.drive_count ?? 0 },
        ]}
      />
      {list.data && <Pager total={list.data.total} limit={LIMIT} offset={offset} onChange={setOffset} />}

      {creating && (
        <FormModal
          title="Add a company"
          submitLabel="Create company"
          onClose={() => setCreating(false)}
          onSubmit={async (values) => {
            const created = await api.post<Company>("/companies", values);
            setFlash(`Added ${created.company_name}.`);
            list.reload();
          }}
          fields={COMPANY_FIELDS()}
        />
      )}
    </>
  );
}

export function CompanyDetail() {
  const { id } = useParams();
  const company = useApi<Company & { drives: Drive[] }>(`/companies/${id}`);
  const [editing, setEditing] = useState(false);
  const c = company.data;

  if (company.loading && !c) return <div className="card"><div className="state">Loading company…</div></div>;
  if (company.error) return <Notice tone="error" title={company.error} />;
  if (!c) return null;

  return (
    <>
      <div className="breadcrumb"><Link to="/companies">Companies</Link> / {c.company_name}</div>
      <div className="page-head">
        <div>
          <h1>{c.company_name}</h1>
          <p>{c.industry ?? "Industry not recorded"} · {c.city ?? "City not recorded"}</p>
        </div>
        <button onClick={() => setEditing(true)}>Edit company</button>
      </div>

      <div className="card">
        <h2>Contact</h2>
        <div className="kv">
          <KV k="HR name" v={c.hr_name} />
          <KV k="HR email" v={c.hr_email} />
          <KV k="HR phone" v={c.hr_phone} />
          <KV k="Website" v={c.website ? <a href={c.website} target="_blank" rel="noreferrer">{c.website}</a> : "—"} />
        </div>
      </div>

      <div className="card">
        <h2>Job drives</h2>
        <DataTable
          rows={c.drives}
          rowKey={(r) => r.drive_id}
          empty="This company has no drive yet."
          columns={[
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
      </div>

      {editing && (
        <FormModal
          title="Edit company"
          submitLabel="Save changes"
          onClose={() => setEditing(false)}
          onSubmit={async (values) => {
            await api.patch(`/companies/${id}`, values);
            company.reload();
          }}
          fields={COMPANY_FIELDS(c)}
        />
      )}
    </>
  );
}
