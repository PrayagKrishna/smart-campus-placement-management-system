import { useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { useApi } from "./useApi";
import { Health } from "./types";

import Dashboard from "./pages/Dashboard";
import Students from "./pages/Students";
import StudentDetail from "./pages/StudentDetail";
import Companies, { CompanyDetail } from "./pages/Companies";
import Drives from "./pages/Drives";
import DriveDetail, { EligibilityCheckPage } from "./pages/DriveDetail";
import Skills from "./pages/Skills";
import Applications, { ApplicationDetail } from "./pages/Applications";
import Interviews from "./pages/Interviews";
import Offers from "./pages/Offers";
import Placements from "./pages/Placements";
import Reports from "./pages/Reports";

const NAV: { group: string; links: [string, string][] }[] = [
  { group: "Overview", links: [["/", "Dashboard"], ["/reports", "Reports"]] },
  {
    group: "Directory",
    links: [
      ["/students", "Students"],
      ["/companies", "Companies"],
      ["/skills", "Skills"],
    ],
  },
  {
    group: "Placement workflow",
    links: [
      ["/drives", "Job drives"],
      ["/applications", "Applications"],
      ["/interviews", "Interviews"],
      ["/offers", "Offers"],
      ["/placements", "Verified placements"],
    ],
  },
];

export default function App() {
  const [navOpen, setNavOpen] = useState(false);
  const health = useApi<Health>("/health");
  const down = health.data?.database !== undefined && health.data.database !== "ok";

  return (
    <div className="shell">
      <div className="mobile-bar">
        <button onClick={() => setNavOpen((v) => !v)} aria-expanded={navOpen}>Menu</button>
        <strong style={{ fontSize: 14 }}>Campus Placement</strong>
      </div>

      <nav className={`sidebar${navOpen ? " open" : ""}`} aria-label="Sections">
        <p className="brand">
          Campus Placement
          <span>Management System · Phase 2</span>
        </p>
        <div className="nav">
          {NAV.map((section) => (
            <div key={section.group}>
              <div className="nav-group">{section.group}</div>
              {section.links.map(([to, label]) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === "/"}
                  onClick={() => setNavOpen(false)}
                  className={({ isActive }) => (isActive ? "active" : "")}
                >
                  {label}
                </NavLink>
              ))}
            </div>
          ))}
        </div>
        <p style={{ fontSize: 11.5, color: "var(--text-muted)", marginTop: 24, padding: "0 6px" }}>
          {down ? "Database unreachable" : health.data?.database_name ?? "connecting…"}
          {health.data?.mysql_version && <><br />MySQL {health.data.mysql_version}</>}
        </p>
      </nav>

      <main className="main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/students" element={<Students />} />
          <Route path="/students/:id" element={<StudentDetail />} />
          <Route path="/companies" element={<Companies />} />
          <Route path="/companies/:id" element={<CompanyDetail />} />
          <Route path="/drives" element={<Drives />} />
          <Route path="/drives/:id" element={<DriveDetail />} />
          <Route path="/drives/:id/check/:studentId" element={<EligibilityCheckPage />} />
          <Route path="/skills" element={<Skills />} />
          <Route path="/applications" element={<Applications />} />
          <Route path="/applications/:id" element={<ApplicationDetail />} />
          <Route path="/interviews" element={<Interviews />} />
          <Route path="/offers" element={<Offers />} />
          <Route path="/placements" element={<Placements />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="*" element={<div className="card"><div className="state">That page does not exist.</div></div>} />
        </Routes>
      </main>
    </div>
  );
}
