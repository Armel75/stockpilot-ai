// ⭐ Client API CENTRALISÉ — tous les appels backend passent par ici.
import type {
  AccuracyLatest,
  AccuracyPoint,
  AgentJob,
  Assertion,
  ForecastSeries,
  Health,
  IngestionLogEntry,
  Pilotage,
  ProductStatus,
  Signal,
} from "@/types";

const BASE = import.meta.env.VITE_API_URL ?? "/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Erreur ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------
// Pilotage
// ---------------------------------------------------------------
export const getPilotage = () => request<Pilotage>("/pilotage");

export const getAssertions = (params?: { priority?: string }) => {
  const q = params?.priority ? `?priority=${params.priority}` : "";
  return request<Assertion[]>(`/assertions${q}`);
};

export const postFeedback = (id: number, feedback: "accurate" | "inaccurate", note?: string) =>
  request<Assertion>(`/assertions/${id}/feedback`, {
    method: "POST",
    body: JSON.stringify({ feedback, note }),
  });

// ---------------------------------------------------------------
// Signaux, prévisions, produits
// ---------------------------------------------------------------
export const getSignals = (signalType?: string) => {
  const q = signalType ? `?signal_type=${signalType}` : "";
  return request<Signal[]>(`/signals${q}`);
};

export const getForecasts = (productRef?: string, limit = 10) => {
  const params = new URLSearchParams({ limit: String(limit) });
  if (productRef) params.set("product_ref", productRef);
  return request<ForecastSeries[]>(`/forecasts?${params}`);
};

export const getProducts = (params?: { q?: string; limit?: number }) => {
  const query = new URLSearchParams();
  if (params?.q) query.set("q", params.q);
  if (params?.limit) query.set("limit", String(params.limit));
  return request<ProductStatus[]>(`/products?${query}`);
};

export const getCategories = () => request<string[]>("/products/categories");

// ---------------------------------------------------------------
// Précision, système, agent
// ---------------------------------------------------------------
export const getAccuracyLatest = () => request<AccuracyLatest>("/accuracy/latest");
export const getAccuracyHistory = () => request<AccuracyPoint[]>("/accuracy/history");

export const getHealth = () => request<Health>("/system/health");
export const getIngestionLogs = () => request<IngestionLogEntry[]>("/system/ingestion-logs");

// Lancement ASYNCHRONE de l'agent : l'API répond immédiatement (job en file),
// sauf repli synchrone si Redis est indisponible (status finished + result).
export const runAgent = (mode?: string) => {
  const q = mode ? `?mode=${mode}` : "";
  return request<AgentJob>(`/system/agent/run${q}`, { method: "POST" });
};

export const getAgentJob = (jobId: string) => request<AgentJob>(`/system/agent/jobs/${jobId}`);

export const getAgentRuns = () => request<AgentJob[]>("/system/agent/runs");
