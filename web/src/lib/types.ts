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
  corporate_name: string | null;
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
  corporate_name: string | null;
  meeting_count: number;
  last_meeting: string | null;
}

export interface CorporationSummary {
  corporation_id: number;
  name: string;
  store_count: number;
  meeting_count: number;
  last_meeting: string | null;
}

export interface StoreIssueSummary {
  company_name: string;
  meeting_count: number;
  last_meeting: string | null;
  issue_count: number;
  has_issues: boolean;
  top_issue: string | null;
}

export interface MeetingSummary {
  company_name: string;
  corporate_name: string | null;
  meeting_uuid: string;
  contact_name: string | null;
  meeting_date: string | null;
  confidence_score: number | null;
  summary: string | null;
}

export interface ListMeetingsResponse {
  success: boolean;
  company_name?: string;
  corporate_name?: string;
  corporations?: CorporationSummary[];
  companies?: CompanySummary[];
  stores?: StoreIssueSummary[];
  meetings?: MeetingSummary[];
  count: number;
}

export interface SearchIssueResult {
  company_name: string;
  corporate_name: string | null;
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
    corporate_name?: string | null;
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
  corporate_name: string | null;
  total_meetings: number;
  latest_record: DiscussionRecordJson;
  all_records: DiscussionRecordJson[];
  stats: Record<string, { count: number; avg_priority: number }>;
  generated_at: string;
}

export interface CorporateCardResponse {
  success: boolean;
  corporate_name: string;
  store_count: number;
  stores_with_issues: number;
  stores: StoreIssueSummary[];
  generated_at: string;
}

export interface ApiError {
  detail: string;
}
