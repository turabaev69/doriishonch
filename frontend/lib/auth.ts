// Xodimlar tokeni (xaridorlar uchun login yoʻq)
export type Session = { token: string; username: string; role: string; role_label: string; display_name: string; manufacturer_id: number | null };

const KEY = "doriishonch_staff";
let memory: Session | null = null;

export function getSession(): Session | null {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Session) : memory;
  } catch {
    return memory;
  }
}

export function setSession(s: Session | null) {
  memory = s;
  try {
    if (s) localStorage.setItem(KEY, JSON.stringify(s));
    else localStorage.removeItem(KEY);
  } catch {}
  if (typeof window !== "undefined") window.dispatchEvent(new Event("doriishonch-auth"));
}
