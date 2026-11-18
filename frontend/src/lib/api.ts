export type User = { id: string; email: string; full_name: string; created_at: string };
export type Agent = { id: string; name: string; description: string; environment: string; framework: string; status: string; active: boolean; created_at: string };
export type Trace = { id: string; agent_id: string; agent_name?: string; trace_id: string; name: string; status: string; input?: string; output?: string; error?: string; started_at: string; ended_at?: string; latency_ms: number; input_tokens: number; output_tokens: number; cost_usd: number; metadata_json?: Record<string, unknown> };
export type DataCase = { id: string; dataset_id: string; input: string; expected_output?: string; actual_output?: string; reference_context?: string; expected_tool?: string; actual_tool?: string; instructions?: string; created_at: string };
export type Dataset = { id: string; name: string; description: string; created_at: string; updated_at: string; cases: DataCase[] };
export type EvalRun = { id: string; dataset_id: string; agent_id?: string; prompt_version_id?: string; name: string; status: string; progress: number; completed_cases: number; total_cases: number; average_score: number; metrics: Record<string, unknown>; error?: string; created_at: string; results?: Array<{ id: string; case_id: string; score: number; metrics: Record<string, number>; passed: boolean; reasoning: string }> };
export type PromptVersion = { id: string; agent_id: string; version: number; label: string; content: string; notes: string; regression_threshold: number; created_at: string };
export type Page<T> = { items: T[]; total: number; page: number; page_size: number };

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) { super(message); this.name = 'ApiError'; this.status = status; }
}

export function token(): string | null { return sessionStorage.getItem('agentops_token'); }
export function signOut(): void { sessionStorage.removeItem('agentops_token'); }

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  const auth = token();
  if (auth) headers.set('Authorization', `Bearer ${auth}`);
  const response = await fetch(`/api${path}`, { ...options, headers });
  if (response.status === 204) return undefined as T;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(body.detail || `Request failed (${response.status})`, response.status);
  return body as T;
}

export function jsonBody(payload: unknown): string { return JSON.stringify(payload); }
export function errorMessage(error: unknown): string { return error instanceof Error ? error.message : 'Something went wrong. Please try again.'; }
export function formatDate(value?: string): string { return value ? new Date(value).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'; }
export function formatNumber(value: number): string { return new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 }).format(value); }
