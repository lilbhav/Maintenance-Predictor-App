const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ---- types ----------------------------------------------------------------

export interface LogEntry {
  id: number;
  timestamp: string;
  machine_id: string;
  temperature: number;
  vibration: number;
  status: "OPERATIONAL" | "WARNING" | "ERROR";
}

export interface LogsResponse {
  total: number;
  page: number;
  page_size: number;
  pages: number;
  logs: LogEntry[];
}

export interface AtRiskMachine {
  machine_id: string;
  risk_level: "high" | "medium" | "low";
  reason: string;
  affected_sensors: string[];
}

export interface AnalysisResult {
  id: number;
  created_at: string;
  status: "success" | "error";
  attempt_count: number;
  error_message: string | null;
  top_machines: { top_3_at_risk: AtRiskMachine[] } | null;
}

export interface AnalysisHistory {
  total: number;
  results: AnalysisResult[];
}

// ---- api calls ------------------------------------------------------------

export const api = {
  ingestCsv: () =>
    request<{ success: boolean; ingested: number; file: string }>("/api/logs/ingest", {
      method: "POST",
    }),

  getLogs: (page: number, pageSize: number, machineId?: string) => {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (machineId) params.set("machine_id", machineId);
    return request<LogsResponse>(`/api/logs?${params}`);
  },

  getMachineIds: () =>
    request<{ machine_ids: string[] }>("/api/logs/machines"),

  runAnalysis: () =>
    request<AnalysisResult>("/api/analysis/run", { method: "POST" }),

  getHistory: () => request<AnalysisHistory>("/api/analysis/history"),

  getAnalysis: (id: number) => request<AnalysisResult>(`/api/analysis/${id}`),
};
