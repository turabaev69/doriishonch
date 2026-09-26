import AsyncStorage from "@react-native-async-storage/async-storage";
import Constants from "expo-constants";
import type {
  Alert, AnalogsResponse, BatchSignal, BoxInspection, ChainStatus, ChatMessage, ChatResponse, DemoCode, DrugBrief, LedgerEntry,
  LeaderRow, Mission, Mode, Participant, PharmacyRisk, ReportReason, RewardItem, StaffSession, MlStatus, MapPharmacy, TrustCard, VerifyResponse,
  Wallet,
} from "./types";
import { getStaff } from "./store";

// Server manzili: veb-ilova manzili (masalan, ./start.sh public bergan https://....trycloudflare.com).
// Ilova unga /api qoʻshib murojaat qiladi (veb-ilova soʻrovlarni backendga uzatadi).
const KEY = "doriishonch_server";
let cached: string | null = null;

// ./start.sh iphone server manzilini mobile/.env ga yozadi (EXPO_PUBLIC_API_URL) — ilova avtomatik ulanadi.
const ENV_URL = (process.env.EXPO_PUBLIC_API_URL || "").replace(/\/+$/, "");

export async function getServer(): Promise<string> {
  if (cached !== null) return cached;
  const saved = await AsyncStorage.getItem(KEY).catch(() => null);
  const url: string = ENV_URL || saved || (Constants.expoConfig?.extra?.apiUrl as string) || "";
  cached = url;
  return url;
}

export async function setServer(url: string) {
  cached = url.trim().replace(/\/+$/, "").replace(/\/api$/, "");
  await AsyncStorage.setItem(KEY, cached);
}

async function req<T>(path: string, init?: RequestInit, staff = false): Promise<T> {
  const server = await getServer();
  if (!server) throw new Error("Server manzili kiritilmagan. Sozlamalar boʻlimiga kiring.");
  const headers = new Headers(init?.headers);
  if (staff) {
    const st = await getStaff();
    if (st) headers.set("Authorization", `Bearer ${st.token}`);
  }
  let r: Response;
  try {
    r = await fetch(`${server}/api${path}`, { ...init, headers });
  } catch {
    throw new Error("Serverga ulanib boʻlmadi. Manzilni va internetni tekshiring.");
  }
  if (r.status === 401 && staff) throw new Error("Xodim sessiyasi tugagan. Qaytadan kiring.");
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail || `Server xatosi (${r.status})`);
  }
  return r.json() as Promise<T>;
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  health: () => req<{ status: string; ai_enabled: boolean; asl_belgisi: boolean }>("/health"),
  pharmacies: () => req<Participant[]>("/pharmacies"),
  nearby: (lat: number, lon: number) =>
    req<{ pharmacy: Participant; distance_m: number }[]>(`/pharmacies/nearby?lat=${lat}&lon=${lon}`),
  verify: (b: { code?: string; gtin?: string; serial?: string; mode: Mode; pharmacy_id?: number | null; device_id: string; price_paid?: number | null }) =>
    req<VerifyResponse>("/verify", json(b)),
  report: (scan_id: number, note: string, reason: ReportReason = "other") =>
    req<{ message: string; pending_points: number }>("/reports", json({ scan_id, note, reason })),
  wallet: (device_id: string) => req<Wallet>(`/rewards/me?device_id=${encodeURIComponent(device_id)}`),
  missions: (device_id: string) => req<Mission[]>(`/missions?device_id=${encodeURIComponent(device_id)}`),
  leaderboard: (device_id: string) => req<LeaderRow[]>(`/rewards/leaderboard?device_id=${encodeURIComponent(device_id)}`),
  catalog: () => req<{ items: RewardItem[]; daily_cap: number }>("/rewards/catalog"),
  redeem: (device_id: string, reward_key: string) =>
    req<{ code: string; title: string; partner: string; points: number; note: string }>("/rewards/redeem", json({ device_id, reward_key })),
  nickname: (device_id: string, nickname: string) => req<{ nickname: string }>("/rewards/nickname", json({ device_id, nickname })),
  chat: (messages: ChatMessage[], device_id: string, lat?: number, lon?: number) =>
    req<ChatResponse>("/ai/chat", json({ messages, device_id, lat, lon })),
  inspectBox: (uri: string, gtin?: string, serial?: string) => {
    const form = new FormData();
    form.append("file", { uri, name: "box.jpg", type: "image/jpeg" } as unknown as Blob);
    if (gtin) form.append("gtin", gtin);
    if (serial) form.append("serial", serial);
    return req<BoxInspection>("/ai/inspect-box", { method: "POST", body: form });
  },
  verifyImage: async (uri: string, mode: Mode, pharmacy_id: number | null | undefined, device_id: string) => {
    const form = new FormData();
    form.append("file", { uri, name: "code.jpg", type: "image/jpeg" } as unknown as Blob);
    form.append("mode", mode);
    form.append("device_id", device_id);
    if (pharmacy_id) form.append("pharmacy_id", String(pharmacy_id));
    return req<VerifyResponse>("/verify/image", { method: "POST", body: form });
  },
  search: (q: string) => req<{ query: string; results: DrugBrief[] }>(`/search?q=${encodeURIComponent(q)}`),
  drug: (id: number | string) => req<TrustCard>(`/drugs/${id}`),
  analogs: (id: number | string) => req<AnalogsResponse>(`/drugs/${id}/analogs`),
  demoCodes: () => req<DemoCode[]>("/demo/codes"),
  ledgerCode: (gtin: string, serial: string) =>
    req<LedgerEntry[]>(`/ledger/code?gtin=${encodeURIComponent(gtin)}&serial=${encodeURIComponent(serial)}`),
  login: (username: string, password: string) => req<StaffSession>("/auth/login", json({ username, password })),
  alerts: (sort: "new" | "ai" = "ai") => req<Alert[]>(`/inspector/alerts?limit=40&sort=${sort}`, undefined, true),
  mlStatus: () => req<MlStatus>("/ml/status"),
  mapPharmacies: () => req<{ center: { lat: number; lon: number; zoom: number }; pharmacies: MapPharmacy[] }>("/map/pharmacies"),
  resolveReport: (scan_id: number, confirmed: boolean) =>
    req<{ status: string; credited: number }>(`/inspector/reports/${scan_id}/resolve`, json({ confirmed }), true),
  batchSignals: () => req<BatchSignal[]>("/inspector/batch-signals", undefined, true),
  risks: () => req<PharmacyRisk[]>("/inspector/pharmacies", undefined, true),
  inspectorChat: (messages: ChatMessage[]) => req<ChatResponse>("/ai/inspector", json({ messages }), true),
  ledgerVerify: () => req<ChainStatus>("/ledger/verify"),
  ledgerLatest: () => req<LedgerEntry[]>("/ledger/latest?limit=40"),
};

export const TOOL_LABEL: Record<string, string> = {
  verify_code: "Qutini tekshirdi", search_drug: "Dorini qidirdi", trust_card: "Ishonch kartasi",
  find_analogs: "Analoglar", code_history: "Zanjir tarixi", nearby_pharmacies: "Yaqin dorixonalar",
  pharmacy_risks: "Dorixonalar xavfi", pharmacy_detail: "Dorixona tafsiloti", recent_alerts: "Signallar",
  ledger_stats: "Zanjir statistikasi", customs_flags: "Bojxona signallari",
};

export const KIND_LABEL: Record<string, string> = {
  scan: "Skanerlandi", purchase: "Sotib olindi (xaridor qayd etdi)", disputed: "Bahsli xarid", report: "Inspektorga xabar",
};

export function fmt(s: string) {
  const d = new Date(s.endsWith("Z") || s.includes("+") ? s : s + "Z");
  const p = (n: number) => String(n).padStart(2, "0");
  return `${p(d.getDate())}.${p(d.getMonth() + 1)}.${d.getFullYear()} ${p(d.getHours())}:${p(d.getMinutes())}`;
}
