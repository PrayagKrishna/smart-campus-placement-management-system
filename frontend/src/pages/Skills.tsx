import { useState } from "react";
import { qs } from "../api";
import { Badge, DataTable, Field } from "../components/ui";
import { useApi } from "../useApi";
import { ReportRun, Skill } from "../types";

const CATEGORIES = ["Programming", "Database", "Web", "Tools", "Soft Skill", "Other"];

export default function Skills() {
  const [category, setCategory] = useState("");
  const [q, setQ] = useState("");
  const list = useApi<Skill[]>(`/skills${qs({ category, q })}`);
  const demand = useApi<ReportRun>("/reports/skill-demand?limit=500");

  type DemandRow = {
    skill_id: number; skill_name: string; skill_category: string;
    drives_requiring: number; drives_mandatory: number; students_having: number;
  };
  const demandRows = (demand.data?.rows ?? []) as DemandRow[];
  const byId = new Map(demandRows.map((r) => [r.skill_id, r]));
  const maxDrives = Math.max(1, ...demandRows.map((r) => r.drives_requiring));

  const rows = (list.data ?? []).map((s) => ({ ...s, demand: byId.get(s.skill_id) }));

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Skills</h1>
          <p>
            The <span className="mono">skill</span> catalogue, with how many drives ask for each
            skill and how many students hold it.
          </p>
        </div>
      </div>

      <div className="filters">
        <Field label="Search" wide>
          <input value={q} placeholder="Skill name" onChange={(e) => setQ(e.target.value)} />
        </Field>
        <Field label="Category">
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="">All</option>
            {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </Field>
      </div>

      <DataTable
        rows={rows}
        loading={list.loading}
        error={list.error}
        rowKey={(r) => r.skill_id}
        empty="No skill matches these filters."
        columns={[
          { header: "Skill", cell: (r) => r.skill_name },
          { header: "Category", cell: (r) => <Badge value={r.skill_category} /> },
          { header: "Drives requiring", num: true, cell: (r) => r.demand?.drives_requiring ?? 0 },
          { header: "Mandatory in", num: true, cell: (r) => r.demand?.drives_mandatory ?? 0 },
          { header: "Students holding", num: true, cell: (r) => r.demand?.students_having ?? 0 },
          {
            header: "Demand",
            cell: (r) => (
              <div className="bar" style={{ minWidth: 90 }}>
                <span style={{ width: `${(100 * (r.demand?.drives_requiring ?? 0)) / maxDrives}%` }} />
              </div>
            ),
          },
        ]}
      />
    </>
  );
}
