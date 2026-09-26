"use client";

import Link from "next/link";
import { useState } from "react";
import { api, fmtDateTime, ReportReason, VerifyResponse } from "@/lib/api";
import { Icon } from "./Icon";
import { NewProductCard } from "./NewProductCard";

const STATUS = {
  ok: { style: "border-brand-100 bg-brand-50 text-brand-900", label: "Tekshiruv natijasi", symbol: "✓" },
  warning: { style: "border-amber-200 bg-amber-50 text-amber-950", label: "Eʼtibor bering", symbol: "!" },
  danger: { style: "border-red-200 bg-red-50 text-red-900", label: "Xavf belgisi", symbol: "!" },
  unknown: { style: "border-slate-200 bg-slate-50 text-slate-800", label: "Tasdiqlanmadi", symbol: "?" },
};
const REASONS: [ReportReason, string][] = [["packaging", "Qadoq shubhali"], ["reused", "Quti qayta ishlatilgan"], ["fake", "Kod shubhali"], ["other", "Boshqa"]];

export function VerifyResult({ r, onPurchase }: { r: VerifyResponse; onPurchase?: (price: number | null) => Promise<void> }) {
  const [buying, setBuying] = useState(false);
  const [price, setPrice] = useState("");
  const [note, setNote] = useState("");
  const [reason, setReason] = useState<ReportReason>("packaging");
  const [reportBusy, setReportBusy] = useState(false);
  const [reported, setReported] = useState(false);
  const [error, setError] = useState("");
  const demo = r.is_demo ?? (r.source === "local" && !!r.drug?.is_demo);
  const status = STATUS[r.source === "crowd" && r.verdict === "ok" ? "unknown" : r.verdict];
  const missingSale = r.checks.some(check => check.key === "sale_not_registered");
  const headline = missingSale && r.verdict === "warning" ? "Sotuv qaydi topilmadi" : r.headline;
  const expiry = r.pack?.expiry ?? r.parsed.expiry;
  const source = demo ? "Demo baza" : r.source === "asl_belgisi" ? "Asl Belgisi" : "Xaridorlar maʼlumoti";
  const summary = demo ? "Namuna maʼlumot. Haqiqiy xarid yoki kassa holatini bildirmaydi."
    : missingSale ? "Sotuv holati yangilanmagan boʻlishi mumkin. Kassa chekini tekshiring."
    : r.source === "crowd" ? "Rasmiy manbada tasdiqlanmagan."
    : r.verdict !== "ok" ? r.advice[0] : "Bu natija dori tarkibini tasdiqlamaydi.";

  async function report() {
    if (!r.scan_id || reportBusy) return;
    setReportBusy(true);
    setError("");
    try { await api.report(r.scan_id, note, reason); setReported(true); }
    catch (failure) { setError((failure as Error).message); }
    finally { setReportBusy(false); }
  }

  return <div className="space-y-4">
    <section className={`rounded-3xl border p-5 sm:p-6 ${status.style}`} aria-label="Quti tekshiruvi">
      <div className="flex items-start gap-3">
        <span aria-hidden="true" className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-white/70 text-2xl font-bold">{status.symbol}</span>
        <div className="min-w-0"><p className="text-sm font-semibold">{demo ? "Namuna natijasi · Demo" : status.label}</p><h2 className="mt-1 text-xl font-extrabold">{headline}</h2></div>
      </div>
      {summary && <p className="mt-3 text-sm">{summary}</p>}
    </section>

    <dl className="card divide-y divide-slate-100 py-2">
      <div className="flex flex-wrap justify-between gap-2 py-3"><dt className="text-sm text-slate-500">Dori</dt><dd className="font-semibold">{r.drug ? `${r.drug.trade_name} ${r.drug.strength}` : r.new_product?.name || "Aniqlanmadi"}</dd></div>
      <div className="flex flex-wrap justify-between gap-2 py-3"><dt className="text-sm text-slate-500">Yaroqlilik muddati</dt><dd className="font-semibold">{expiry ? expiry.split("-").reverse().join(".") : "Maʼlumot yoʻq"}</dd></div>
      <div className="flex flex-wrap justify-between gap-2 py-3"><dt className="text-sm text-slate-500">Manba</dt><dd className="font-semibold">{source}</dd></div>
    </dl>

    {r.reward && (r.reward.earned > 0 || r.reward.pending > 0) && <Link href="/ballar" className="reward-card"><span className="step-symbol"><Icon name="star" /></span><div><strong>{r.reward.earned ? `+${r.reward.earned} demo ball` : `${r.reward.pending} ball kutilmoqda`}</strong><p>Jami: {r.reward.total} ball</p></div><Icon name="chevron" size={19} /></Link>}

    {onPurchase && r.scan_id && r.verdict !== "danger" && <section className="card space-y-3">
      <h3 className="font-bold">Sotib oldingizmi?</h3>
      <div className="flex flex-col gap-2 sm:flex-row"><input aria-label="Toʻlagan narxingiz, soʻm, ixtiyoriy" inputMode="numeric" className="text-input min-w-0 flex-1" placeholder="Narxi, soʻm (ixtiyoriy)" value={price} onChange={event => setPrice(event.target.value.replace(/\D/g, ""))} /><button type="button" className="primary-button" disabled={buying} onClick={async () => { setBuying(true); try { await onPurchase(price ? Number(price) : null); } finally { setBuying(false); } }}>{buying ? "Saqlanmoqda…" : "Sotib oldim"}</button></div>
      <p className="text-sm text-slate-500">Xaridingiz ilovada qayd etiladi. Bu kassa cheki emas.</p>
    </section>}

    {r.new_product && !r.new_product.name && <NewProductCard p={r.new_product} />}

    <details className="card">
      <summary className="font-semibold">Batafsil maʼlumot</summary>
      <div className="mt-4 space-y-4">
        {r.drug && <p className="text-sm">{r.drug.inn} · {r.drug.manufacturer.name}</p>}
        <ul className="space-y-3">{r.checks.map(check => <li key={check.key} className="text-sm"><p className="font-semibold">{check.title}</p><p className="text-slate-600">{check.text}</p></li>)}</ul>
        {r.chain.length > 0 && <section><h3 className="font-semibold">Quti tarixi</h3><ol className="mt-2 space-y-2">{r.chain.map((event, index) => <li key={`${event.type}:${index}`} className="text-sm"><strong>{event.label}</strong><p className="text-slate-600">{event.participant} · {fmtDateTime(event.at)}</p></li>)}</ol></section>}
        {r.drug && <Link href={`/drug/${r.drug.id}`} className="subtle-link">Dori haqida<Icon name="arrow" size={17} /></Link>}
      </div>
    </details>

    {r.scan_id && <details className="card"><summary className="font-semibold">Muammo haqida xabar</summary>{reported ? <p role="status" className="mt-3">Xabaringiz saqlandi.</p> : <form className="mt-3 space-y-3" onSubmit={event => { event.preventDefault(); report(); }}><label className="field-label" htmlFor="report-reason">Muammo turi</label><select id="report-reason" value={reason} onChange={event => setReason(event.target.value as ReportReason)} className="text-input">{REASONS.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select><label className="field-label" htmlFor="report-note">Izoh (ixtiyoriy)</label><input id="report-note" className="text-input" value={note} maxLength={1000} onChange={event => setNote(event.target.value)} /><button className="secondary-button" disabled={reportBusy}>{reportBusy ? "Yuborilmoqda…" : "Xabar yuborish"}</button>{error && <p role="alert" className="error-notice">{error}</p>}</form>}</details>}
  </div>;
}
