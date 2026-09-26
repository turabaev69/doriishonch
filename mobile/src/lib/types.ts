export type Participant = { id: number; kind: string; name: string; region: string; address: string; license_ok: boolean; is_demo: boolean; lat?: number | null; lon?: number | null };
export type DrugBrief = {
  id: number; trade_name: string; inn: string; strength: string; form: string; atc_group: string;
  price_uzs: number; pack_size: string; prescription_only: boolean; is_demo: boolean;
  manufacturer: { id: number; name: string; country: string; is_local: boolean; is_demo: boolean };
};
export type Check = { key: string; status: "ok" | "info" | "warning" | "danger"; title: string; text: string };
export type ChainEvent = { type: string; label: string; participant: string; participant_kind: string; region: string; at: string; document: string };
export type LedgerEntry = {
  index: number; hash: string; prev_hash: string; created_at: string; kind: string;
  gtin: string; serial: string; pharmacy: string; region: string; verdict: string; is_demo: boolean;
};
export type Mode = "before" | "after";
export type VerifyResponse = {
  verdict: "ok" | "warning" | "danger" | "unknown"; headline: string; explanation: string; ai_used: boolean;
  checks: Check[]; advice: string[]; parsed: { gtin?: string; serial?: string };
  drug: DrugBrief | null;
  pack: { gtin: string; serial: string; batch: string; expiry: string; status: string; status_label: string; owner: Participant | null } | null;
  chain: ChainEvent[]; dispense: { category: string; label: string; note: string } | null;
  scan_id: number | null; source: "local" | "asl_belgisi" | "crowd";
  ledger: { block: LedgerEntry | null; history: LedgerEntry[] } | null;
  reward?: Reward | null;
  ai_risk?: AiRisk | null;
};
/** Oʻz modelimiz (skan xavf modeli): signal, xulosa emas */
export type AiRisk = { score: number; level: "past" | "oʻrta" | "yuqori"; reasons: { text: string; impact: number }[]; model: string };
export type MlStatus = {
  risk: {
    version: string; trained_at: string; n_synthetic: number; n_real: number;
    metrics: { synthetic_holdout: { roc_auc: number; pr_auc: number; rules_only_roc_auc: number; rules_only_pr_auc: number } };
  } | null;
  packnet: { version: string; classes: { gtin: string; name: string }[]; metrics_val_synthetic: Record<string, unknown>; notes: string } | null;
  labeled_reports: number; retrain_every: number; training: boolean;
};
export type Reward = { earned: number; pending: number; messages: string[]; total: number; level: string };
export type ChatMessage = { role: "user" | "assistant"; content: string };
export type ChatResponse = { answer: string; steps: { tool: string; input: Record<string, unknown>; summary: string }[]; ai_used: boolean; blocked: boolean };
export type BoxInspection = {
  ai_used: boolean; overall: "ok" | "warning" | "unknown"; summary: string; checks: Check[];
  model?: import("./packnet").PackResult | null;
};
export type ChainStatus = { ok: boolean; blocks: number; broken_at: number | null; reason: string; last_hash: string };
export type Fact = {
  key: string; label: string; status: "ok" | "warn" | "missing" | "info"; text: string;
  source_url: string | null; updated_at: string | null; provided_by_manufacturer: boolean; is_demo: boolean;
};
export type TrustCard = { drug: DrugBrief; facts: Fact[]; disclaimer: string };
export type Analog = {
  drug: DrugBrief; price_diff_uzs: number; price_diff_pct: number; has_valid_gmp: boolean;
  quality_alert_count: number; evidence_count: number;
};
export type AnalogsResponse = { base: DrugBrief; analogs: Analog[]; note: string };
export type StaffSession = { token: string; username: string; role: string; role_label: string; display_name: string };
export type Alert = {
  scan_id: number; at: string; verdict: string; reasons: string[]; mode: string; region: string;
  pharmacy: string; drug: string; serial: string; reported: boolean; report_note: string;
  report_reason: string; report_status: string; price_paid: number | null; ml_score: number | null;
};
export type BatchSignal = {
  drug: string; batch: string; reports: number; quality_reports: number; regions: string[];
  reasons: Record<string, number>; level: string; note: string;
};
export type PharmacyRisk = {
  pharmacy: Participant; level: string; anomaly: number; ml_outlier: boolean; received: number; sold: number;
  sell_through: number; in_stock: number; stale: number; scans: number; reuse: number; unregistered: number;
  clone: number; reports: number; signals: string[];
};
export type DemoCode = {
  key: string; title: string; expected: string; mode: Mode; pharmacy_id: number | null; pharmacy_name: string;
  trade_name: string; code: string; code_display: string;
};
export type Level = { name: string; icon: string; min: number; next_name: string | null; next_min: number | null; progress: number; index: number };
export type Badge = { key: string; icon: string; title: string; description: string; earned: boolean };
export type PointHistory = { id: number; kind: string; label: string; points: number; status: string; note: string; at: string };
export type Wallet = {
  nickname: string; has_nickname: boolean; flagged: boolean; points: number; pending: number; lifetime: number;
  level: Level; today: { earned: number; cap: number }; streak: number; badges: Badge[]; rank: number | null;
  history: PointHistory[]; redemptions: { reward_key: string; title: string; code: string; points: number; at: string }[];
  rules: { kind: string; label: string; points: number }[];
};
export type Mission = {
  id: string; pharmacy_id: number; pharmacy: string; region: string; address: string; points: number; done: boolean;
  scanners_this_week: number; title: string; why: string; expires: string;
};
export type LeaderRow = { rank: number; name: string; points: number; region: string; me: boolean };
export type RewardItem = { key: string; title: string; partner: string; points: number; icon: string };
export type ReportReason = "fake" | "reused" | "no_effect" | "packaging" | "price" | "other";

export type MapPharmacy = {
  id: number; name: string; region: string; region_key: string | null; address: string; lat: number; lon: number;
  license_ok: boolean; is_demo: boolean; checks_30d?: number; last_check?: string | null; mission_points?: number | null;
  distance_m?: number; osm?: boolean;
};
