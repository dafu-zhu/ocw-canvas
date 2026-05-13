export interface User {
  id: string;
  email: string;
  display_name: string;
}

export type CourseStatus = "active" | "completed" | "planned";
export type ModuleItemKind = "link" | "video" | "assignment" | "note" | "header";

export interface Course {
  id: string;
  code: string;
  title: string;
  institution: string;
  term_label: string;
  instructor: string;
  external_home_url: string;
  textbook: string;
  home_page_md: string;
  syllabus_md: string;
  description: string;
  color: string;
  status: CourseStatus;
  display_order: number;
}

export interface ModuleItem {
  id: string;
  module_id: string;
  position: number;
  indent: number;
  kind: ModuleItemKind;
  title: string;
  external_url: string;
  assignment_id: string | null;
  text_md: string;
  published: boolean;
}

export interface Module {
  id: string;
  course_id: string;
  title: string;
  position: number;
  published: boolean;
  items: ModuleItem[];
}

export interface AssignmentGroup {
  id: string;
  course_id: string;
  name: string;
  weight: number | null;
  drop_lowest_n: number;
  position: number;
}

export interface AssignmentSummary {
  id: string;
  title: string;
  points_possible: number;
  due_at: string | null;
  assignment_group_id: string | null;
  published: boolean;
}

export interface CourseDetail extends Course {
  modules: Module[];
  assignment_groups: AssignmentGroup[];
  assignments: AssignmentSummary[];
}

export type LatePolicy = "none" | "flag_only" | "percent_per_day";

export interface Assignment {
  id: string;
  course_id: string;
  assignment_group_id: string | null;
  title: string;
  description_md: string;
  points_possible: number;
  due_at: string | null;
  available_at: string | null;
  accepts_files: boolean;
  accepts_text: boolean;
  official_solution_url: string;
  official_solution_file_path: string;
  late_policy: LatePolicy;
  late_value: number | null;
  position: number;
  published: boolean;
}

export interface RubricItem {
  criterion: string;
  points_awarded: number;
  points_possible: number;
  note: string;
}

export interface Grade {
  id: string;
  submission_id: string;
  score: number;
  score_out_of: number;
  late_penalty_applied: number;
  final_score: number;
  percentage: number;
  feedback_md: string;
  rubric_breakdown: RubricItem[];
  graded_by: string;
  model: string;
  graded_at: string | null;
}

export interface Submission {
  id: string;
  assignment_id: string;
  attempt_number: number;
  submitted_at: string | null;
  is_late: boolean;
  text_body: string | null;
  file_paths: string[];
  source: string;
  status: string;
  grade: Grade | null;
}

export interface AssignmentDetail extends Assignment {
  submissions: Submission[];
}

export interface GradebookRow {
  assignment_id: string;
  title: string;
  group_name: string;
  points_possible: number;
  due_at: string | null;
  submitted_at: string | null;
  status: string;
  score: number | null;
  feedback_md: string;
  rubric_breakdown: RubricItem[];
}

export interface GradebookGroup {
  name: string;
  weight: number | null;
  drop_lowest_n: number;
  percentage: number | null;
  earned: number;
  possible: number;
}

export interface Gradebook {
  course_id: string;
  rows: GradebookRow[];
  groups: GradebookGroup[];
  total_percentage: number | null;
  only_graded: boolean;
}

export type AiSolutionStatus = "pending" | "generating" | "ready" | "failed";

export interface AiSolution {
  id: string;
  assignment_id: string;
  status: AiSolutionStatus;
  content_md: string;
  model: string;
  prompt_log_path: string;
  generated_at: string | null;
  error: string;
}

export interface SolutionInfo {
  assignment_id: string;
  key_kind: "official_url" | "official_file" | "ai" | "none";
  official_solution_url: string;
  ai_available: boolean;
  generation_available: boolean;
  ai_solution: AiSolution | null;
}

export interface Announcement {
  id: string;
  course_id: string | null;
  kind: "graded" | "deadline" | "manual" | "system";
  title: string;
  body_md: string;
  related_assignment_id: string | null;
  read_at: string | null;
  emailed_at: string | null;
  created_at: string;
}
