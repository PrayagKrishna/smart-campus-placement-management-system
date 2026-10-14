/** Shapes returned by the Phase 2 API. They mirror the Phase 1 columns. */

export type Department = { dept_id: number; dept_code: string; dept_name: string };

export type Skill = { skill_id: number; skill_name: string; skill_category: string };

export type Student = {
  student_id: number;
  reg_no: string;
  first_name: string;
  last_name: string | null;
  email: string;
  phone: string | null;
  dob: string | null;
  gender: string | null;
  dept_id: number;
  dept_code: string | null;
  dept_name: string | null;
  batch_year: number;
  cgpa: string;
  active_backlogs: number;
  tenth_pct: string | null;
  twelfth_pct: string | null;
  resume_link: string | null;
};

export type StudentSkill = Skill & { proficiency_level: string };

export type StudentDetail = Student & {
  skills: StudentSkill[];
  applications: {
    application_id: number;
    drive_id: number;
    applied_on: string;
    application_status: string;
    job_title: string;
    company_name: string;
    ctc_lpa: string;
    drive_status: string;
    offer_id: number | null;
    offer_status: string | null;
    offered_ctc_lpa: string | null;
    interview_rounds: number;
  }[];
  placement: Record<string, unknown> | null;
  is_placed: boolean;
};

export type Company = {
  company_id: number;
  company_name: string;
  industry: string | null;
  website: string | null;
  hr_name: string;
  hr_email: string;
  hr_phone: string | null;
  city: string | null;
  drive_count?: number;
};

export type Drive = {
  drive_id: number;
  company_id: number;
  company_name: string;
  job_title: string;
  job_type: string;
  job_description: string | null;
  ctc_lpa: string;
  job_location: string | null;
  num_openings: number;
  apply_deadline: string;
  drive_date: string;
  drive_status: string;
  application_count?: number;
};

export type Criteria = {
  drive_id: number;
  min_cgpa: string;
  max_backlogs: number;
  min_tenth_pct: string;
  min_twelfth_pct: string;
  eligible_batch_year: number;
  allow_placed_students: boolean;
};

export type DriveDetail = Drive & {
  eligibility_criteria: Criteria | null;
  eligible_departments: Department[];
  required_skills: (Skill & { is_mandatory: boolean; min_proficiency: string })[];
  application_count: number;
  offer_count: number;
};

export type Application = {
  application_id: number;
  student_id: number;
  drive_id: number;
  applied_on: string;
  application_status: string;
  remarks: string | null;
  reg_no: string;
  student_name: string;
  job_title: string;
  company_name: string;
  company_id: number;
  ctc_lpa: string;
  drive_status: string;
};

export type Interview = {
  interview_id: number;
  application_id: number;
  round_no: number;
  round_type: string;
  mode: string;
  scheduled_at: string;
  venue: string | null;
  interviewer_name: string | null;
  score: string | null;
  max_score: string | null;
  result: string;
  feedback: string | null;
  reg_no?: string;
  student_name?: string;
  job_title?: string;
  company_name?: string;
};

export type Offer = {
  offer_id: number;
  application_id: number;
  offer_date: string;
  role_title: string;
  offered_ctc_lpa: string;
  job_location: string | null;
  expected_joining_date: string | null;
  offer_status: string;
  student_id: number;
  reg_no: string;
  student_name: string;
  company_name: string;
};

export type Placement = {
  placement_id: number;
  offer_id: number;
  actual_joining_date: string | null;
  company_employee_code: string | null;
  academic_year: string;
  verified_by: string;
  verified_on: string;
  remarks: string | null;
  student_id: number;
  reg_no: string;
  student_name: string;
  batch_year: number;
  dept_code: string;
  dept_name: string;
  company_name: string;
  offered_ctc_lpa: string;
  role_title: string;
};

export type ApplicationDetail = Application & {
  interviews: Interview[];
  offer: Offer | null;
  placement: Placement | null;
};

export type EligibilityCheck = {
  student_id: number;
  drive_id: number;
  eligible: boolean;
  criteria_defined: boolean;
  department_restricted: boolean;
  reasons: string[];
  checks: { name: string; required: unknown; actual: unknown; passed: boolean }[];
};

export type SkillMatch = {
  required_count: number;
  matched_count: number;
  mandatory_count: number;
  mandatory_matched: number;
  all_mandatory_met: boolean;
  skills: {
    skill_id: number;
    skill_name: string;
    is_mandatory: boolean;
    min_proficiency: string;
    proficiency_level: string | null;
    held: boolean;
    meets_proficiency: boolean;
  }[];
};

export type Dashboard = {
  totals: {
    students: number; departments: number; skills: number; companies: number;
    job_drives: number; open_drives: number; applications: number;
    interviews: number; interviews_pending: number; offers_issued: number;
    offers_accepted: number; verified_placements: number;
    placement_percentage: number;
    average_accepted_ctc_lpa: number | null;
    highest_offer_ctc_lpa: number | null;
  };
  applications_by_status: { application_status: string; count: number }[];
  offers_by_status: { offer_status: string; count: number }[];
};

export type Health = {
  api: string;
  database: string;
  database_name: string | null;
  mysql_version: string | null;
  table_count: number | null;
  detail: string | null;
};

export type ReportMeta = { name: string; description: string };
export type ReportRun = {
  name: string;
  description: string;
  rows: Record<string, unknown>[];
  row_count: number;
};
