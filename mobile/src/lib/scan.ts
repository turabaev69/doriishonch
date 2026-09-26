import { api } from "./api";
import { getDeviceId } from "./device";
import { addHistory, getPharmacy, HistoryItem } from "./store";
import type { Mode } from "./types";

/** Kodni tekshiradi, natijani tarixga yozadi va saqlangan yozuvni qaytaradi. */
export async function runVerify(code: string, mode: Mode, price?: number | null): Promise<HistoryItem> {
  const pharmacy = await getPharmacy();
  const r = await api.verify({ code, mode, pharmacy_id: pharmacy?.id, device_id: await getDeviceId(), price_paid: price ?? null });
  return addHistory({ code, mode, pharmacy: pharmacy?.name ?? null, result: r });
}

export async function runVerifyImage(uri: string, mode: Mode): Promise<HistoryItem> {
  const pharmacy = await getPharmacy();
  const r = await api.verifyImage(uri, mode, pharmacy?.id, await getDeviceId());
  const code = r.parsed.gtin ? `01${r.parsed.gtin}21${r.parsed.serial ?? ""}` : "";
  return addHistory({ code, mode, pharmacy: pharmacy?.name ?? null, result: r });
}
