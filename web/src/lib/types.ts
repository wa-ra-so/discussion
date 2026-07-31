export interface PriorityIssue {
  category: string;
  issue: string;
  priority: number | null;
}

export interface DxSolutions {
  revenue_maximization?: string[];
  efficiency_cost_reduction?: string[];
  recruitment_market_development?: string[];
}

export interface ProcessResult {
  success: boolean;
  meeting_id: string;
  company_name: string;
  contact_name: string;
  confidence_score: number;
  summary: string;
  priority_issues: PriorityIssue[];
  dx_solutions: DxSolutions;
  created_at: string;
}

export interface CompanySummary {
  company_id: number;
  name: string;
  meeting_count: number;
  last_meeting: string | null;
}

export interface MeetingSummary {
  company_name: string;
  meeting_uuid: string;
  contact_name: string | null;
  meeting_date: string | null;
  confidence_score: number | null;
  summary: string | null;
}

export interface ListMeetingsResponse {
  success: boolean;
  company_name?: string;
  companies?: CompanySummary[];
  meetings?: MeetingSummary[];
  count: number;
}

export interface SearchIssueResult {
  company_name: string;
  category: string;
  issue: string;
  priority: number | null;
  meeting_date: string | null;
}

export interface SearchResponse {
  success: boolean;
  query: string;
  issues: SearchIssueResult[];
  count: number;
}

export interface DiscussionRecordJson {
  meeting_id: string;
  company_info: {
    name: string;
    contact_name: string;
    contact_email?: string | null;
    date: string;
  };
  discussions: Record<string, unknown>;
  priority_issues: PriorityIssue[];
  dx_solutions: DxSolutions;
  next_steps: Record<string, unknown>;
  summary: string | null;
  confidence_score: number;
  created_at: string;
  notes?: string | null;
}

export interface CardResponse {
  success: boolean;
  company_name: string;
  total_meetings: number;
  latest_record: DiscussionRecordJson;
  all_records: DiscussionRecordJson[];
  stats: Record<string, { count: number; avg_priority: number }>;
  generated_at: string;
}

export interface ApiError {
  detail: string;
}
