import { getSession, Session, setSession } from "./auth";

// Standart: frontend bilan bir manzil (/api → backend, next.config.ts dagi rewrites).
// Shunda telefon yoki tunnel orqali ochilganda ham faqat bitta manzil kerak boʻladi.
export const API_URL = process.env.NEXT_PUBLIC_API_URL || "/api";

export type Manufacturer = {
  id: number;
  name: string;
  country: string;
  is_local: boolean;
  is_demo: boolean;
};

export type DrugBrief = {
  id: number;
  trade_name: string;
  inn: string;
  strength: string;
  form: string;
  atc_group: string;
  price_uzs: number;
  pack_size: string;
  prescription_only: boolean;
  is_demo: boolean;
  manufacturer: Manufacturer;
};

export type Fact = {
  key: string;
  label: string;
  status: "ok" | "warn" | "missing" | "info";
  text: string;
  source_url: string | null;
  updated_at: string | null;
  provided_by_manufacturer: boolean;
  is_demo: boolean;
};

export type TrustCard = { drug: DrugBrief; facts: Fact[]; disclaimer: string };

export type Analog = {
  drug: DrugBrief;
  price_diff_uzs: number;
  price_diff_pct: number;
  has_valid_gmp: boolean;
  quality_alert_count: number;
  evidence_count: number;
};

export type AnalogsResponse = { base: DrugBrief; analogs: Analog[]; note: string };
export type ExplainResponse = { answer: string; sources: Fact[]; blocked: boolean; ai_used: boolean };
export type ScanResponse = { extracted: Record<string, string | null>; matches: DrugBrief[]; method: string; note: string };

export type Insights = {
  manufacturer: Manufacturer;
  total_views: number;
  total_questions: number;
  drugs: { drug: DrugBrief; views: number; questions: number }[];
  topics: { topic: string; label: string; count: number }[];
  competing_imports: Analog[];
};

export type Participant = {
  id: number;
  kind: string;
  name: string;
  region: string;
  address: string;
  license_ok: boolean;
  is_demo: boolean;
  lat?: number | null;
  lon?: number | null;
};

export type Check = { key: string; status: "ok" | "info" | "warning" | "danger"; title: string; text: string };

export type ChainEvent = {
  type: string;
  label: string;
  participant: string;
  participant_kind: string;
  region: string;
  at: string;
  document: string;
};

export type VerifyResponse = {
  is_demo?: boolean;
  verdict: "ok" | "warning" | "danger" | "unknown";
  headline: string;
  explanation: string;
  ai_used: boolean;
  checks: Check[];
  advice: string[];
  parsed: { gtin?: string; serial?: string; batch?: string; expiry?: string | null };
  drug: DrugBrief | null;
  pack: {
    gtin: string;
    serial: string;
    batch: string;
    expiry: string;
    status: string;
    status_label: string;
    owner: Participant | null;
  } | null;
  chain: ChainEvent[];
  dispense: { category: string; label: string; note: string } | null;
  scan_id: number | null;
  source: "local" | "asl_belgisi" | "crowd";
  ledger: { block: LedgerEntry | null; history: LedgerEntry[] } | null;
  reward?: Reward | null;
  ai_risk?: AiRisk | null;
  places?: Place[];
  new_product?: { gtin: string; name: string; scans: number; is_new: boolean; has_location: boolean } | null;
};

export type Place = { kind: string; label: string; lat: number; lon: number; at: string | null; place: string; me: boolean };
export type CrowdProduct = {
  gtin: string; name: string; scans: number; first_seen: string; last_seen: string;
  lat: number | null; lon: number | null; region: string; pharmacy: string; gtin_valid: boolean;
};
export type MapPharmacy = {
  id: number; name: string; region: string; region_key: string | null; address: string; lat: number; lon: number;
  license_ok: boolean; is_demo: boolean; checks_30d?: number; last_check?: string | null; mission_points?: number | null;
  level?: "yuqori" | "oʻrta" | "past"; signals?: string[]; distance_m?: number; osm?: boolean;
};

/** Oʻz modelimiz (skan xavf modeli): signal, xulosa emas */
export type AiRisk = { score: number; level: "past" | "oʻrta" | "yuqori"; reasons: { text: string; impact: number }[]; model: string };
export type MlStatus = {
  risk: {
    version: string; trained_at: string; algorithm: string; n_synthetic: number; n_real: number; notes: string;
    metrics: {
      synthetic_holdout: { roc_auc: number; pr_auc: number; rules_only_roc_auc: number; rules_only_pr_auc: number; n: number };
      real_labeled: { n: number; positives: number };
    };
  } | null;
  packnet: (import("./packnet").PackCard & { trained_at: string; train: { synthetic: number; real: number } }) | null;
  training: boolean;
  labeled_reports: number;
  retrain_every: number;
};

export type Reward = { earned: number; pending: number; messages: string[]; total: number; level: string };
export type Level = { name: string; icon: string; min: number; next_name: string | null; next_min: number | null; progress: number; index: number };
export type Wallet = {
  nickname: string; has_nickname: boolean; flagged: boolean; points: number; pending: number; lifetime: number;
  level: Level; today: { earned: number; cap: number }; streak: number; rank: number | null;
  badges: { key: string; icon: string; title: string; description: string; earned: boolean }[];
  history: { id: number; kind: string; label: string; points: number; status: string; note: string; at: string }[];
  redemptions: { reward_key: string; title: string; code: string; points: number; at: string }[];
  rules: { kind: string; label: string; points: number }[];
};
export type Mission = {
  id: string; pharmacy_id: number; pharmacy: string; region: string; address: string; points: number; done: boolean;
  scanners_this_week: number; title: string; why: string; expires: string;
};
export type LeaderRow = { rank: number; name: string; points: number; region: string; me: boolean };
export type RewardItem = { key: string; title: string; partner: string; points: number; icon: string };
export type ReportReason = "fake" | "reused" | "no_effect" | "packaging" | "price" | "other";
export type BatchSignal = {
  drug: string; batch: string; reports: number; quality_reports: number; regions: string[];
  reasons: Record<string, number>; level: string; note: string;
};

export type LedgerEntry = {
  index: number;
  hash: string;
  prev_hash: string;
  created_at: string;
  kind: "scan" | "purchase" | "disputed" | "report";
  gtin: string;
  serial: string;
  pharmacy: string;
  region: string;
  verdict: string;
  is_demo: boolean;
};

export type ChatMessage = { role: "user" | "assistant"; content: string };
export type ChatRequest = {
  messages: ChatMessage[];
  pharmacy_id?: number | null;
  device_id?: string;
  lat?: number | null;
  lon?: number | null;
};
export type ChatResponse = {
  answer: string;
  steps: { tool: string; input: Record<string, unknown>; summary: string }[];
  ai_used: boolean;
  blocked: boolean;
};
export type BoxInspection = {
  ai_used: boolean;
  overall: "ok" | "warning" | "unknown";
  summary: string;
  checks: { key: string; status: string; title: string; text: string }[];
  observed: Record<string, unknown>;
  model?: import("./packnet").PackResult | null;
};

export const TOOL_LABEL: Record<string, string> = {
  verify_code: "Qutini tekshirdi",
  search_drug: "Dorini qidirdi",
  trust_card: "Ishonch kartasini oʻqidi",
  find_analogs: "Analoglarni topdi",
  code_history: "Zanjir tarixini koʻrdi",
  nearby_pharmacies: "Yaqin dorixonalarni topdi",
  pharmacy_risks: "Dorixonalar xavfini koʻrdi",
  pharmacy_detail: "Dorixona tafsilotlari",
  recent_alerts: "Ogohlantirishlarni koʻrdi",
  ledger_stats: "Zanjir statistikasi",
  customs_flags: "Bojxona belgilarini koʻrdi",
};

export type ChainStatus = { ok: boolean; blocks: number; broken_at: number | null; reason: string; last_hash: string };
export type NearbyPharmacy = { pharmacy: Participant; distance_m: number };

export type Mode = "before" | "after";

export type VerifyInput = {
  code?: string;
  gtin?: string;
  serial?: string;
  mode: Mode;
  pharmacy_id?: number | null;
  device_id?: string;
  price_paid?: number | null;
  lat?: number | null;
  lon?: number | null;
};

export type DemoCode = {
  key: string;
  title: string;
  expected: string;
  mode: Mode;
  pharmacy_id: number | null;
  pharmacy_name: string;
  trade_name: string;
  code: string;
  code_display: string;
};

export type CustomsLine = {
  id: number;
  description: string;
  gtin: string;
  batch: string;
  quantity: number;
  registered_packs: number;
  match_method: string;
  drug: DrugBrief | null;
  flags: string[];
};

export type Declaration = {
  id: number;
  number: string;
  cleared_at: string;
  customs_post: string;
  importer: Participant;
  origin_country: string;
  source: string;
  is_demo: boolean;
  lines: CustomsLine[];
  flag_count: number;
};

export type PharmacyRisk = {
  pharmacy: Participant;
  level: "yuqori" | "oʻrta" | "past";
  anomaly: number;
  ml_outlier: boolean;
  received: number;
  sold: number;
  sell_through: number;
  in_stock: number;
  stale: number;
  scans: number;
  reuse: number;
  unregistered: number;
  clone: number;
  reports: number;
  signals: string[];
};

export type PharmacyRiskDetail = PharmacyRisk & { summary: string; ai_used: boolean };

export type Alert = {
  scan_id: number;
  at: string;
  verdict: string;
  reasons: string[];
  mode: string;
  region: string;
  pharmacy: string;
  drug: string;
  serial: string;
  reported: boolean;
  report_note: string;
  report_reason: string;
  report_status: string;
  price_paid: number | null;
  ml_score: number | null;
};

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const session = typeof window !== "undefined" ? getSession() : null;
  const headers = new Headers(init?.headers);
  if (session) headers.set("Authorization", `Bearer ${session.token}`);
  const r = await fetch(`${API_URL}${path}`, { cache: "no-store", ...init, headers });
  if (r.status === 401 && typeof window !== "undefined" && !path.startsWith("/auth/")) {
    setSession(null);
    window.location.href = `/kirish?keyin=${encodeURIComponent(window.location.pathname)}`;
    throw new Error("Kirish talab qilinadi");
  }
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(body.detail || `Server xatosi (${r.status})`);
  }
  return r.json();
}

export const api = {
  search: (q: string) => req<{ results: DrugBrief[] }>(`/search?q=${encodeURIComponent(q)}`),
  card: (id: number) => req<TrustCard>(`/drugs/${id}`),
  analogs: (id: number) => req<AnalogsResponse>(`/drugs/${id}/analogs`),
  explain: (drug_id: number, question: string) =>
    req<ExplainResponse>(`/explain`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ drug_id, question }),
    }),
  scan: (form: FormData) => req<ScanResponse>(`/scan`, { method: "POST", body: form }),
  manufacturers: () => req<Manufacturer[]>(`/manufacturers`),
  insights: (id: number) => req<Insights>(`/manufacturers/${id}/insights`),

  pharmacies: () => req<Participant[]>(`/pharmacies`),
  verify: (body: VerifyInput) =>
    req<VerifyResponse>(`/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  verifyImage: (form: FormData) => req<VerifyResponse>(`/verify/image`, { method: "POST", body: form }),
  report: (scan_id: number, note: string, reason: ReportReason = "other") =>
    req<{ ok: boolean; message: string; pending_points: number }>(`/reports`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scan_id, note, reason }),
    }),
  wallet: (device_id: string) => req<Wallet>(`/rewards/me?device_id=${encodeURIComponent(device_id)}`),
  missions: (device_id: string) => req<Mission[]>(`/missions?device_id=${encodeURIComponent(device_id)}`),
  leaderboard: (device_id: string) => req<LeaderRow[]>(`/rewards/leaderboard?device_id=${encodeURIComponent(device_id)}`),
  rewardCatalog: () => req<{ items: RewardItem[]; daily_cap: number }>(`/rewards/catalog`),
  redeem: (device_id: string, reward_key: string) =>
    req<{ code: string; title: string; partner: string; points: number; note: string }>(`/rewards/redeem`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ device_id, reward_key }),
    }),
  nickname: (device_id: string, nickname: string) =>
    req<{ nickname: string }>(`/rewards/nickname`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ device_id, nickname }),
    }),
  resolveReport: (scan_id: number, confirmed: boolean) =>
    req<{ scan_id: number; status: string; credited: number }>(`/inspector/reports/${scan_id}/resolve`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ confirmed }),
    }),
  batchSignals: () => req<BatchSignal[]>(`/inspector/batch-signals`),
  demoCodes: () => req<DemoCode[]>(`/demo/codes`),
  declarations: () => req<Declaration[]>(`/customs/declarations`),
  customsSync: () => req<Declaration[]>(`/customs/sync`, { method: "POST" }),
  ingestDeclaration: (data: unknown) =>
    req<Declaration>(`/customs/declarations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  risk: () => req<PharmacyRisk[]>(`/inspector/pharmacies`),
  riskDetail: (id: number) => req<PharmacyRiskDetail>(`/inspector/pharmacies/${id}`),
  alerts: (sort: "new" | "ai" = "new") => req<Alert[]>(`/inspector/alerts?sort=${sort}`),
  mlStatus: () => req<MlStatus>(`/ml/status`),
  mapPharmacies: () => req<{ center: { lat: number; lon: number; zoom: number }; pharmacies: MapPharmacy[] }>(`/map/pharmacies`),
  mapInspector: () => req<MapPharmacy[]>(`/map/inspector`),
  mapProducts: () => req<CrowdProduct[]>(`/map/products`),
  mapScans: () => req<{ lat: number; lon: number }[]>(`/map/scans`),
  nameProduct: (gtin: string, name: string) =>
    req<CrowdProduct>(`/map/products/${gtin}/name`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name }),
    }),
  mlRetrain: () => req<NonNullable<MlStatus["risk"]>>(`/ml/retrain`, { method: "POST" }),
  nearby: (lat: number, lon: number) => req<NearbyPharmacy[]>(`/pharmacies/nearby?lat=${lat}&lon=${lon}`),
  ledgerVerify: () => req<ChainStatus>(`/ledger/verify`),
  ledgerLatest: (limit = 30) => req<LedgerEntry[]>(`/ledger/latest?limit=${limit}`),
  login: (username: string, password: string) =>
    req<Session>(`/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    }),
  demoAccounts: () => req<{ username: string; password: string; role: string }[]>(`/auth/demo-accounts`),
  aiStatus: () => req<{ ai_enabled: boolean; model: string | null; features: string[] }>(`/ai/status`),
  chat: (body: ChatRequest) =>
    req<ChatResponse>(`/ai/chat`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
  copilot: (messages: ChatMessage[]) =>
    req<ChatResponse>(`/ai/inspector`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages }),
    }),
  inspectBox: (form: FormData) => req<BoxInspection>(`/ai/inspect-box`, { method: "POST", body: form }),
  ledgerCode: (gtin: string, serial: string) =>
    req<LedgerEntry[]>(`/ledger/code?gtin=${encodeURIComponent(gtin)}&serial=${encodeURIComponent(serial)}`),
};

export const KIND_LABEL: Record<string, string> = {
  scan: "Skanerlandi",
  purchase: "Sotib olindi (xaridor qayd etdi)",
  disputed: "Bahsli xarid",
  report: "Inspektorga xabar",
};

export function fmtDateTime(s: string) {
  const d = new Date(s.endsWith("Z") || s.includes("+") ? s : s + "Z");
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export const som = (n: number) => `${n.toLocaleString("ru-RU").replace(/,/g, " ")} soʻm`;
