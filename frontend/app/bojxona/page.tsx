"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, Declaration, fmtDateTime } from "@/lib/api";

const METHOD: Record<string, string> = {
  gtin: "GTIN boʻyicha",
  fuzzy: "Tavsif boʻyicha (matn)",
  ai: "Tavsif boʻyicha (AI)",
  none: "Moslanmadi",
};

const SAMPLE = `{
  "number": "26001/250926/0009001",
  "cleared_at": "2026-09-25T12:00:00",
  "customs_post": "Toshkent-AERO bojxona posti",
  "importer_tin": "300000101",
  "origin_country": "Hindiston",
  "lines": [
    {
      "description": "BISOPROLOL FUMARATE 5MG TABLETS N30 GANGA",
      "batch": "BS-1001",
      "quantity": 3,
      "serials": ["BSNEW00000001", "BSNEW00000002", "BSNEW00000003"]
    }
  ]
}`;

export default function Customs() {
  const [decls, setDecls] = useState<Declaration[] | null>(null);
  const [open, setOpen] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [json, setJson] = useState(SAMPLE);
  const [showForm, setShowForm] = useState(false);
  const [onlyFlagged, setOnlyFlagged] = useState(false);

  const load = () => api.declarations().then(setDecls).catch((e) => setMsg(e.message));
  useEffect(() => {
    load();
  }, []);

  async function sync() {
    setBusy(true);
    setMsg("");
    try {
      const n = await api.customsSync();
      setMsg(n.length ? `Bojxonadan ${n.length} ta yangi deklaratsiya olindi va tekshirildi.` : "Yangi deklaratsiya yoʻq.");
      if (n[0]) setOpen(n[0].id);
      await load();
    } catch (e) {
      setMsg((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function ingest(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMsg("");
    try {
      const d = await api.ingestDeclaration(JSON.parse(json));
      setMsg(`Deklaratsiya ${d.number} qabul qilindi.`);
      setOpen(d.id);
      setShowForm(false);
      await load();
    } catch (e) {
      setMsg((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const total = decls?.reduce((a, d) => a + d.lines.reduce((b, l) => b + l.registered_packs, 0), 0) ?? 0;
  const flagged = decls?.filter((d) => d.flag_count > 0).length ?? 0;
  const shown = (decls ?? []).filter((d) => !onlyFlagged || d.flag_count > 0);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Bojxona integratsiyasi</h1>
          <p className="max-w-2xl text-sm text-gray-600">
            Bojxonadan oʻtgan har bir dori partiyasi tizimga kiritiladi: tovar reestrga moslanadi, seriya raqamlari qutilar
            sifatida roʻyxatga olinadi va xavfli holatlar belgilanadi. Xaridor skanerlaganda qutining bojxona yozuvi koʻrinadi.
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowForm(!showForm)} className="rounded-lg bg-white px-4 py-2 text-sm font-medium ring-1 ring-gray-300">
            Qoʻlda yuklash (JSON)
          </button>
          <button onClick={sync} disabled={busy} className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
            {busy ? "…" : "Bojxonadan sinxronlash"}
          </button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Stat label="Deklaratsiyalar" value={decls?.length ?? "…"} />
        <Stat label="Roʻyxatga olingan qutilar" value={total} />
        <Stat label="Ogohlantirishli deklaratsiyalar" value={flagged} warn={flagged > 0} />
      </div>

      {msg && <p className="rounded-lg bg-brand-50 p-3 text-sm text-brand-700">{msg}</p>}

      {showForm && (
        <form onSubmit={ingest} className="space-y-2 rounded-2xl border border-gray-200 bg-white p-5">
          <p className="text-sm text-gray-600">
            Bojxona tizimi API si yuboradigan format. GTIN koʻrsatilmasa, tizim tavsifni reestrga oʻzi moslaydi.
          </p>
          <textarea value={json} onChange={(e) => setJson(e.target.value)} rows={14} className="w-full rounded-lg border border-gray-300 p-3 font-mono text-xs" />
          <button disabled={busy} className="rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white">
            Yuklash va tekshirish
          </button>
        </form>
      )}

      <label className="flex items-center gap-2 text-sm text-gray-600">
        <input type="checkbox" checked={onlyFlagged} onChange={(e) => setOnlyFlagged(e.target.checked)} />
        Faqat ogohlantirishlilarni koʻrsatish
      </label>

      <div className="space-y-3">
        {shown.map((d) => (
          <div key={d.id} className={`rounded-2xl border bg-white ${d.flag_count ? "border-amber-300" : "border-gray-200"}`}>
            <button onClick={() => setOpen(open === d.id ? null : d.id)} className="flex w-full flex-wrap items-center justify-between gap-2 p-4 text-left">
              <div>
                <div className="font-mono text-sm font-semibold">BYD {d.number}</div>
                <div className="text-sm text-gray-600">
                  {fmtDateTime(d.cleared_at)} · {d.customs_post} · {d.origin_country} → {d.importer.name}
                </div>
              </div>
              <div className="flex items-center gap-2">
                {d.source !== "demo" && <span className="rounded bg-indigo-50 px-2 py-0.5 text-xs text-indigo-700">{d.source}</span>}
                {d.flag_count > 0 ? (
                  <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">{d.flag_count} ta ogohlantirish</span>
                ) : (
                  <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800">muammo yoʻq</span>
                )}
              </div>
            </button>
            {open === d.id && (
              <div className="border-t border-gray-100 p-4">
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[720px] text-sm">
                    <thead className="text-left text-gray-500">
                      <tr>
                        <th className="px-2 py-1 font-medium">Tavsif (deklaratsiyadan)</th>
                        <th className="px-2 py-1 font-medium">Reestrdagi dori</th>
                        <th className="px-2 py-1 font-medium">Partiya</th>
                        <th className="px-2 py-1 text-right font-medium">Soni</th>
                        <th className="px-2 py-1 text-right font-medium">Roʻyxatga olingan</th>
                      </tr>
                    </thead>
                    <tbody>
                      {d.lines.map((l) => (
                        <tr key={l.id} className="border-t border-gray-50 align-top">
                          <td className="px-2 py-2">
                            <div>{l.description}</div>
                            {l.flags.map((f) => (
                              <div key={f} className="mt-1 text-xs text-amber-800">⚠ {f}</div>
                            ))}
                          </td>
                          <td className="px-2 py-2">
                            {l.drug ? (
                              <Link href={`/drug/${l.drug.id}`} className="text-brand-700 hover:underline">
                                {l.drug.trade_name} {l.drug.strength}
                              </Link>
                            ) : (
                              <span className="text-red-700">topilmadi</span>
                            )}
                            <div className="text-xs text-gray-500">{METHOD[l.match_method] ?? l.match_method}</div>
                          </td>
                          <td className="px-2 py-2 font-mono text-xs">{l.batch}</td>
                          <td className="px-2 py-2 text-right">{l.quantity}</td>
                          <td className="px-2 py-2 text-right">{l.registered_packs}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
      <p className="text-xs text-gray-500">
        Demo manba: sinxronlash har safar tayyor roʻyxatdan bitta yangi deklaratsiya keltiradi. Haqiqiy integratsiya uchun
        backend .env faylida CUSTOMS_API_URL koʻrsatiladi (Bojxona qoʻmitasi bilan kelishuvdan keyin).
      </p>
    </div>
  );
}

function Stat({ label, value, warn = false }: { label: string; value: string | number; warn?: boolean }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4">
      <div className="text-sm text-gray-500">{label}</div>
      <div className={`mt-1 text-2xl font-semibold ${warn ? "text-amber-700" : ""}`}>{value}</div>
    </div>
  );
}
