import AsyncStorage from "@react-native-async-storage/async-storage";
import type { Participant, StaffSession, VerifyResponse } from "./types";

// Qurilmadagi maʼlumotlar: skanerlash tarixi, tanlangan dorixona, xodim sessiyasi.
// Hech narsa serverga yuborilmaydi (tarix faqat shu telefonda).

const HISTORY = "doriishonch_history";
const PHARMACY = "doriishonch_pharmacy";
const STAFF = "doriishonch_staff";
const MAX = 100;

export type HistoryItem = {
  id: string;
  at: string;
  code: string;
  mode: "before" | "after";
  pharmacy: string | null;
  result: VerifyResponse;
};

async function read<T>(key: string, fallback: T): Promise<T> {
  try {
    const raw = await AsyncStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

async function write(key: string, value: unknown) {
  try {
    if (value === null) await AsyncStorage.removeItem(key);
    else await AsyncStorage.setItem(key, JSON.stringify(value));
  } catch {}
}

export async function getHistory(): Promise<HistoryItem[]> {
  return read<HistoryItem[]>(HISTORY, []);
}

export async function addHistory(item: Omit<HistoryItem, "id" | "at">): Promise<HistoryItem> {
  const full: HistoryItem = { ...item, id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`, at: new Date().toISOString() };
  const list = await getHistory();
  await write(HISTORY, [full, ...list].slice(0, MAX));
  return full;
}

export async function clearHistory() {
  await write(HISTORY, null);
}

export async function getPharmacy(): Promise<Participant | null> {
  return read<Participant | null>(PHARMACY, null);
}

export async function setPharmacy(p: Participant | null) {
  await write(PHARMACY, p);
}

let staffCache: StaffSession | null | undefined;
export async function getStaff(): Promise<StaffSession | null> {
  if (staffCache === undefined) staffCache = await read<StaffSession | null>(STAFF, null);
  return staffCache;
}

export async function setStaff(s: StaffSession | null) {
  staffCache = s;
  await write(STAFF, s);
}

/** Sotib olingan (mode=after) qutilar: muddati bilan. */
export function purchases(list: HistoryItem[]) {
  const seen = new Set<string>();
  return list
    .filter((h) => h.mode === "after" && h.result.pack && h.result.verdict !== "danger")
    .filter((h) => {
      const k = `${h.result.pack!.gtin}/${h.result.pack!.serial}`;
      if (seen.has(k)) return false;
      seen.add(k);
      return true;
    })
    .map((h) => ({ item: h, daysLeft: daysUntil(h.result.pack!.expiry) }));
}

export function daysUntil(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return null;
  return Math.floor((t - Date.now()) / 86400000);
}
