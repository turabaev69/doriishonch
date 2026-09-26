"use client";

import { useEffect, useState } from "react";
import { api, PriceSummary } from "@/lib/api";
import { getDeviceId } from "@/lib/device";

const money = (amount: number) => `${new Intl.NumberFormat("uz-UZ").format(amount)} soʻm`;

export function PriceCard({ scanId, onSaved }: { scanId: number; onSaved: (price: number) => void }) {
  const [value, setValue] = useState("");
  const [summary, setSummary] = useState<PriceSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [skipped, setSkipped] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    api.priceSummary(scanId, getDeviceId()).then(data => {
      if (cancelled) return;
      setSummary(data);
      if (data.saved_price) onSaved(data.saved_price);
    }).catch(() => { if (!cancelled) setError("Narxlar yuklanmadi. Narxni saqlashda qayta uriniladi."); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [scanId, onSaved]);

  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (busy) return;
    const clean = value.replace(/\s/g, "");
    const amount = Number(clean);
    if (!/^[0-9]+$/.test(clean) || !Number.isSafeInteger(amount) || amount < 1 || amount > 100_000_000) {
      setError("1 dan 100 000 000 soʻmgacha butun narx kiriting.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const data = await api.savePrice(scanId, getDeviceId(), amount);
      setSummary(data);
      onSaved(amount);
    } catch (failure) { setError((failure as Error).message); }
    finally { setBusy(false); }
  }

  const difference = summary?.difference_percent;
  return <section className="card space-y-3" aria-label="Xarid narxi" aria-busy={busy || loading}>
    {summary?.saved_price ? <div role="status"><p className="text-sm text-slate-500">{summary.is_demo ? "Demo narx saqlandi" : "Narxingiz saqlandi"}</p><h3 className="mt-1 text-xl font-extrabold">{money(summary.saved_price)}</h3></div>
      : skipped ? <button className="subtle-link" onClick={() => setSkipped(false)}>Xarid narxini qoʻshish</button>
      : <form onSubmit={save} className="space-y-3">
        <label htmlFor={`price-${scanId}`} className="block text-lg font-bold">Necha pulga sotib oldingiz?</label>
        <p id={`price-help-${scanId}`} className="text-sm text-slate-500">Butun quti uchun, soʻmda. Ixtiyoriy.</p>
        <input id={`price-${scanId}`} aria-describedby={`price-help-${scanId}`} inputMode="numeric" autoComplete="off" maxLength={15} value={value} onChange={event => setValue(event.target.value)} placeholder="Masalan, 25 000" className="text-input w-full" disabled={busy || loading} />
        <div className="flex flex-wrap gap-2"><button type="submit" className="primary-button" disabled={busy || loading || !value.trim()}>{busy ? "Saqlanmoqda…" : "Narxni saqlash"}</button><button type="button" className="secondary-button" disabled={busy} onClick={() => { setSkipped(true); setError(""); }}>Hozir emas</button></div>
      </form>}
    {error && <p role="alert" className="error-notice text-sm">{error}</p>}
    {summary && <div className="border-t border-slate-100 pt-3 text-sm">
      {summary.is_demo ? <p className="text-slate-500">Demo narxlar haqiqiy narxlarga qoʻshilmaydi.</p>
        : summary.median_price != null ? <div className="space-y-2">
          <p className="font-semibold">{summary.region || "Xaridorlar"}: odatiy narx {money(summary.median_price)}</p>
          {difference != null && <p>{difference === 0 ? "Sizning narxingiz odatiy narxga teng." : `Sizning narxingiz ${Math.abs(difference)}% ${difference > 0 ? "qimmatroq" : "arzonroq"}.`}</p>}
          <p className="text-slate-500">{summary.sample_count} ta boshqa xaridor · oxirgi {summary.period_days} kun · bir xil quti kodi.</p>
          <p className="text-slate-500">Narxlar xaridorlar kiritgan maʼlumot, chek bilan tasdiqlanmagan.</p>
        </div> : <p className="text-slate-500">Solishtirish uchun kamida 3 ta boshqa xaridor narxi kerak.</p>}
    </div>}
  </section>;
}
