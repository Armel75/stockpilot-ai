// Types alignés sur les schémas Pydantic du backend

export type Priority = "P0" | "P1" | "P2";
export type Feedback = "none" | "accurate" | "inaccurate";

export interface EvidenceItem {
  label: string;
  value: number | string;
}

export interface Assertion {
  id: number;
  report_date: string;
  priority: Priority;
  type: string;
  title: string;
  message: string;
  product_ref?: string | null;
  product_name?: string | null;
  confidence: number;
  action: string;
  evidence?: EvidenceItem[] | null;
  feedback: Feedback;
  created_at: string;
}

export interface Kpis {
  nb_ruptures: number;
  nb_overstock: number;
  nb_dormant: number;
  nb_opportunities: number;
  nb_reappro: number;
  avg_coverage_days: number;
  nb_products: number;
}

export interface Freshness {
  data_date?: string | null;
  is_fresh: boolean;
  source?: string | null;
  message: string;
}

export interface Decision {
  priority: Priority;
  action_type: string;
  product_ref: string;
  product_name: string;
  quantity?: number | null;
  message: string;
  role: string;
}

export interface Pilotage {
  report_date: string;
  summary: string;
  kpis: Kpis;
  freshness: Freshness;
  assertions: Assertion[];
  decisions: Decision[];
  agent_last_run?: string | null;
}

export interface Signal {
  id: number;
  product_ref: string;
  product_name: string;
  signal_type: string;
  priority: Priority;
  status: string;
  metrics?: Record<string, unknown> | null;
  computed_at: string;
}

export interface ForecastPoint {
  date: string;
  low: number;
  mid: number;
  high: number;
}

export interface ForecastSeries {
  product_ref: string;
  product_name: string;
  horizon_days: number;
  points: ForecastPoint[];
}

export interface ProductStatus {
  product: {
    id: number;
    ref: string;
    name: string;
    category?: string | null;
    brand?: string | null;
    unit_price: number;
    margin_rate: number;
    supplier?: string | null;
    lead_time_days: number;
    min_order_qty: number;
  };
  stock: number;
  coverage_days: number | null;
  daily_avg_30: number;
  open_signals: string[];
}

export interface AccuracyLatest {
  has_score: boolean;
  score_date?: string | null;
  mape?: number | null;
  bias?: number | null;
  sample_size: number;
  message?: string | null;
}

export interface AccuracyPoint {
  score_date: string;
  mape: number | null;
  bias: number | null;
  sample_size: number;
}

export interface AgentRunResult {
  status: string;
  message: string;
  data_source: string;
  nb_products: number;
  nb_forecast: number;
  nb_signals: number;
  nb_assertions: number;
  llm_used: boolean;
  duration_seconds: number;
}

export interface AgentJob {
  job_id?: string | null;
  status: "queued" | "started" | "finished" | "failed";
  mode?: string | null;
  result?: AgentRunResult | null;
  error?: string | null;
}

export interface Health {
  status: string;
  app: string;
  nb_products: number;
  nb_sales: number;
  data_date?: string | null;
  ingestion_mode: string;
  last_ingestion?: string | null;
  deepseek_configured: boolean;
}

export interface IngestionLogEntry {
  id: number;
  source: string;
  status: string;
  rows_loaded: number;
  message: string;
  started_at: string;
  finished_at?: string | null;
}
