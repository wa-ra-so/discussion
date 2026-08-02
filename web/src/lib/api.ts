import type {
  CardResponse,
  CorporateCardResponse,
  ListMeetingsResponse,
  ProcessResult,
  SearchResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiRequestError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = "ApiRequestError";
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore parse errors, use statusText
    }
    throw new ApiRequestError(detail, response.status);
  }
  return response.json() as Promise<T>;
}

export async function analyzeTranscript(params: {
  transcript: string;
  companyName: string;
  corporateName?: string;
  contactName?: string;
  meetingDate?: string;
  notes?: string;
}): Promise<ProcessResult> {
  const formData = new FormData();
  formData.append("transcript", params.transcript);
  formData.append("company_name", params.companyName);
  if (params.corporateName) formData.append("corporate_name", params.corporateName);
  if (params.contactName) formData.append("contact_name", params.contactName);
  if (params.meetingDate) formData.append("meeting_date", params.meetingDate);
  if (params.notes) formData.append("notes", params.notes);

  const response = await fetch(`${API_BASE}/api/process`, {
    method: "POST",
    body: formData,
  });

  return handleResponse<ProcessResult>(response);
}

export async function listMeetings(params?: {
  companyName?: string;
  corporateName?: string;
  limit?: number;
}): Promise<ListMeetingsResponse> {
  const searchParams = new URLSearchParams();
  if (params?.companyName) searchParams.set("company_name", params.companyName);
  if (params?.corporateName) searchParams.set("corporate_name", params.corporateName);
  if (params?.limit) searchParams.set("limit", String(params.limit));

  const response = await fetch(
    `${API_BASE}/api/list-meetings?${searchParams.toString()}`,
  );

  return handleResponse<ListMeetingsResponse>(response);
}

export async function searchIssues(params: {
  query: string;
  limit?: number;
}): Promise<SearchResponse> {
  const searchParams = new URLSearchParams({ query: params.query });
  if (params.limit) searchParams.set("limit", String(params.limit));

  const response = await fetch(
    `${API_BASE}/api/search?${searchParams.toString()}`,
  );

  return handleResponse<SearchResponse>(response);
}

export async function getCompanyCard(companyName: string): Promise<CardResponse> {
  const response = await fetch(
    `${API_BASE}/api/card/${encodeURIComponent(companyName)}`,
  );

  return handleResponse<CardResponse>(response);
}

export async function getCorporateCard(
  corporateName: string,
): Promise<CorporateCardResponse> {
  const response = await fetch(
    `${API_BASE}/api/corporate-card/${encodeURIComponent(corporateName)}`,
  );

  return handleResponse<CorporateCardResponse>(response);
}

export async function checkHealth(): Promise<{ status: string; timestamp: string }> {
  const response = await fetch(`${API_BASE}/api/health`);
  return handleResponse(response);
}
