"use client";

import { useEffect, useState } from "react";
import { api, fmtDateTime, MlStatus } from "@/lib/api";

const pct = (v: unknown) => (typeof v === "number" ? `${Math.round(v * 100)}%` : "—");

/** Oʻz modellarimiz holati: sifat koʻrsatkichlari va qayta oʻqitish. */
export function MlPanel({ tick = 0, canRetrain = true }: { tick?: number; canRetrain?: boolean }) {
  const [s, setS] = useState<MlStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    api.mlStatus().then(setS).catch(() => {});
  }, [tick]);

  async function retrain() {
    setBusy(true);
    setMsg("");
    try {
      const card = await api.mlRetrain();
      setMsg(`Qayta oʻqitildi: ${card.n_real} ta tasdiqlangan holat qoʻshildi.`);
      setS(await api.mlStatus());
    } catch (e) {
      setMsg((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (!s) return null;
  const r = s.risk, h = r?.metrics.synthetic_holdout;
  const p = s.packnet, pm = (p?.metrics_val_synthetic ?? {}) as Record<string, number>;

  return (
    <section className="rounded-2xl border border-indigo-200 bg-white p-5">
      <h2 className="font-semibold">🧠 Oʻz AI modellarimiz</h2>
      <div className="mt-3 grid gap-4 md:grid-cols-2">
        {r && h && (
          <div className="rounded-xl bg-indigo-50/60 p-4">
            <div className="font-semibold">Skan xavf modeli</div>
            <p className="text-xs text-slate-500">Har bir skan uchun qalbaki boʻlish ehtimoli: quti tarixi, narx, dorixona va partiya signallari.</p>
            <div className="mt-3 grid grid-cols-2 gap-2 text-center">
              <Stat label="Model aniqligi (AUC)" value={h.roc_auc.toFixed(2)} />
              <Stat label="Faqat qoidalar" value={h.rules_only_roc_auc.toFixed(2)} muted />
            </div>
            <ul className="mt-3 space-y-1 text-xs text-slate-600">
              <li>• Oʻqitilgan: {r.n_synthetic.toLocaleString()} simulyatsiya + <b>{r.n_real}</b> ta inspektor tasdigʻi</li>
              <li>• Hal qilingan xabarlar: {s.labeled_reports} · har {s.retrain_every} ta yangisidan keyin oʻzi qayta oʻqiydi</li>
              <li>• Oxirgi oʻqitish: {fmtDateTime(r.trained_at)}{s.training ? " · hozir oʻqitilmoqda…" : ""}</li>
            </ul>
            {canRetrain && (
              <button onClick={retrain} disabled={busy}
                className="mt-3 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50">
                {busy ? "Oʻqitilmoqda…" : "Hozir qayta oʻqitish"}
              </button>
            )}
            {msg && <p className="mt-2 text-xs text-slate-600">{msg}</p>}
          </div>
        )}
        {p && (
          <div className="rounded-xl bg-violet-50/60 p-4">
            <div className="font-semibold">Qadoq surati modeli (PackNet)</div>
            <p className="text-xs text-slate-500">Telefonda internetsiz ishlaydi: quti qaysi dori ekanini va asl dizayndan farqini baholaydi.</p>
            <div className="mt-3 grid grid-cols-3 gap-2 text-center">
              <Stat label="Dorini taniydi" value={pct(pm.product_acc_known)} />
              <Stat label="Qalbakini topadi" value={pct(pm.fake_recall_at_threshold)} />
              <Stat label="Asl qutiga xato" value={pct(pm.genuine_flagged_at_threshold)} muted />
            </div>
            <ul className="mt-3 space-y-1 text-xs text-slate-600">
              <li>• {p.classes.length - 1} ta demo dori · {p.train?.synthetic?.toLocaleString()} ta sintetik surat{p.train?.real ? ` + ${p.train.real} ta haqiqiy` : ""}</li>
              <li>• {p.notes}</li>
            </ul>
          </div>
        )}
      </div>
    </section>
  );
}

function Stat({ label, value, muted = false }: { label: string; value: string; muted?: boolean }) {
  return (
    <div className="rounded-lg bg-white p-2">
      <div className={`text-xl font-bold ${muted ? "text-slate-400" : "text-slate-900"}`}>{value}</div>
      <div className="text-[11px] leading-tight text-slate-500">{label}</div>
    </div>
  );
}
