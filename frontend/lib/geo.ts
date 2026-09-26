"use client";

/** Joriy joylashuv (ixtiyoriy). Ruxsat berilmasa yoki sekin boʻlsa — null, tekshiruv kutib qolmaydi. */
let cached: { lat: number; lon: number; at: number } | null = null;

export function getLocation(timeoutMs = 4000): Promise<{ lat: number; lon: number } | null> {
  if (cached && Date.now() - cached.at < 5 * 60_000) return Promise.resolve(cached);
  if (typeof navigator === "undefined" || !navigator.geolocation) return Promise.resolve(null);
  return new Promise((resolve) => {
    const t = setTimeout(() => resolve(null), timeoutMs);
    navigator.geolocation.getCurrentPosition(
      (p) => {
        clearTimeout(t);
        cached = { lat: p.coords.latitude, lon: p.coords.longitude, at: Date.now() };
        resolve(cached);
      },
      () => { clearTimeout(t); resolve(null); },
      { enableHighAccuracy: false, timeout: timeoutMs, maximumAge: 300_000 },
    );
  });
}

/** Dori kodi boʻlishi mumkinmi: GS1 matn, raqamli shtrix-kod yoki GS1 Digital Link. Reklama QR — yoʻq. */
export function looksLikeMedicineCode(text: string): boolean {
  const s = text.replace(/^[\x1d\s]+/, "").trim();
  if (/^(https?:\/\/|www\.|t\.me\/|tg:\/\/)/i.test(s)) return /\/01\/\d{8,14}/.test(s);
  if (/^\d{8,14}$/.test(s)) return true;
  if (/^(\]d2|\]Q3|\]C1)?\(?01\)?\d{14}/.test(s)) return true;
  return /\(01\)\d{14}/.test(s);
}
