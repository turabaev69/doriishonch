"use client";

import { useEffect, useState } from "react";
import { Alert, api, fmtDateTime, PharmacyRisk, PharmacyRiskDetail, BatchSignal } from "@/lib/api";
import { ChatBox } from "@/components/ChatBox";
import { MlPanel } from "@/components/MlPanel";
import { PharmacyMap } from "@/components/PharmacyMap";

const LEVEL: Record<string, string> = {
  yuqori: "bg-red-100 text-red-800",
  "oʻrta": "bg-amber-100 text-amber-800",
  past: "bg-emerald-100 text-emerald-800",
};

export default function Inspector() {
  const [rows, setRows] = useState<PharmacyRisk[] | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [batches, setBatches] = useState<BatchSignal[]>([]);
  const [sort, setSort] = useState<"new" | "ai">("ai");
  const [mlTick, setMlTick] = useState(0);

  async function resolve(scanId: number, confirmed: boolean) {
    await api.resolveReport(scanId, confirmed).catch(() => {});
    api.alerts(sort).then(setAlerts).catch(() => {});
    setMlTick((t) => t + 1);
    api.batchSignals().then(setBatches).catch(() => {});
  }
  const [selected, setSelected] = useState<number | null>(null);
  const [detail, setDetail] = useState<PharmacyRiskDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .risk()
      .then((r) => {
        setRows(r);
        if (r[0]) setSelected(r[0].pharmacy.id);
      })
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    api.alerts(sort).then(setAlerts).catch(() => {});
  }, [sort]);

  useEffect(() => {
    if (selected == null) return;
    setDetail(null);
    api.riskDetail(selected).then(setDetail).catch((e) => setError(e.message));
  }, [selected]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Inspektor paneli</h1>
        <p className="max-w-3xl text-sm text-gray-600">
          Xaridorlar skanerlashlari va markirovka hodisalaridan dorixonalar boʻyicha xavf signallari. Signal tekshiruvni
          rejalashtirish uchun, qoidabuzarlik isboti emas.
        </p>
      </div>
      {error && <p className="rounded-lg bg-red-50 p-3 text-red-700">{error}</p>}

      <section className="rounded-2xl border border-indigo-200 bg-white p-5">
        <h2 className="mb-2 font-semibold">🕵️ AI copilot</h2>
        <ChatBox
          intro="Maʼlumotlar haqida oddiy tilda soʻrang. Copilot xavf signallari, ogohlantirishlar, zanjir va bojxona maʼlumotlaridan foydalanadi."
          placeholder="Masalan: Samarqandda oxirgi hafta nima boʻldi?"
          suggestions={[
            "Qaysi dorixonalarni birinchi navbatda tekshirish kerak va nega?",
            "Oxirgi 7 kunda qayta ishlatilgan qutilar qayerda koʻp?",
            "Bojxonada qanday xavfli importlar bor?",
          ]}
          send={(m) => api.copilot(m)}
        />
      </section>

      <div className="grid gap-6 lg:grid-cols-5">
        <section className="rounded-2xl border border-gray-200 bg-white p-4 lg:col-span-3">
          <h2 className="mb-2 font-semibold">Dorixonalar</h2>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px] text-sm">
              <thead className="text-left text-gray-500">
                <tr>
                  <th className="px-2 py-1 font-medium">Dorixona</th>
                  <th className="px-2 py-1 font-medium">Xavf</th>
                  <th className="px-2 py-1 text-right font-medium">Qayta quti</th>
                  <th className="px-2 py-1 text-right font-medium">Kassasiz sotuv</th>
                  <th className="px-2 py-1 text-right font-medium">Rasmiy sotuv</th>
                </tr>
              </thead>
              <tbody>
                {rows?.map((r) => (
                  <tr
                    key={r.pharmacy.id}
                    onClick={() => setSelected(r.pharmacy.id)}
                    className={`cursor-pointer border-t border-gray-50 hover:bg-gray-50 ${selected === r.pharmacy.id ? "bg-brand-50" : ""}`}
                  >
                    <td className="px-2 py-2">
                      <div className="font-medium">{r.pharmacy.name}</div>
                      <div className="text-xs text-gray-500">{r.pharmacy.region}</div>
                    </td>
                    <td className="px-2 py-2">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${LEVEL[r.level]}`}>{r.level}</span>
                      {r.ml_outlier && <span className="ml-1 text-xs text-purple-700" title="IsolationForest gʻayrioddiy deb topdi">ML</span>}
                    </td>
                    <td className="px-2 py-2 text-right">{r.reuse}</td>
                    <td className="px-2 py-2 text-right">{r.unregistered}</td>
                    <td className="px-2 py-2 text-right">{Math.round(r.sell_through * 100)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="rounded-2xl border border-gray-200 bg-white p-5 lg:col-span-2">
          {!detail ? (
            <p className="text-gray-500">Yuklanmoqda…</p>
          ) : (
            <div className="space-y-3">
              <div>
                <h2 className="text-lg font-semibold">{detail.pharmacy.name}</h2>
                <p className="text-sm text-gray-500">
                  {detail.pharmacy.region}, {detail.pharmacy.address}
                </p>
              </div>
              <div className="rounded-lg bg-gray-50 p-3 text-sm text-gray-800">
                <div className="mb-1 text-xs font-medium text-gray-500">{detail.ai_used ? "AI xulosasi" : "Avtomatik xulosa"}</div>
                {detail.summary}
              </div>
              {detail.signals.length > 0 && (
                <ul className="space-y-1 text-sm">
                  {detail.signals.map((s) => (
                    <li key={s} className="flex gap-2">
                      <span className="text-amber-600">⚠</span>
                      {s}
                    </li>
                  ))}
                </ul>
              )}
              <dl className="grid grid-cols-2 gap-2 text-sm">
                {(
                  [
                    ["Qabul qilingan qutilar", detail.received],
                    ["Rasmiy sotilgan", `${detail.sold} (${Math.round(detail.sell_through * 100)}%)`],
                    ["Qoldiq", detail.in_stock],
                    ["90 kundan eski qoldiq", detail.stale],
                    ["Xaridor skanerlashlari", detail.scans],
                    ["Shikoyatlar", detail.reports],
                    ["ML gʻayrioddiylik", detail.anomaly.toFixed(2)],
                  ] as [string, string | number][]
                ).map(([k, v]) => (
                  <div key={k} className="rounded-lg border border-gray-100 p-2">
                    <dt className="text-xs text-gray-500">{k}</dt>
                    <dd className="font-medium">{v}</dd>
                  </div>
                ))}
              </dl>
            </div>
          )}
        </section>
      </div>

      <section className="space-y-2">
        <h2 className="font-semibold">Xavf xaritasi</h2>
        <PharmacyMap mode="risk" height="460px" />
      </section>

      <MlPanel tick={mlTick} />

      <section className="rounded-2xl border border-gray-200 bg-white p-5">
        <h2 className="font-semibold">Partiya signallari (farmakonazorat)</h2>
        <p className="mb-2 text-xs text-gray-500">Bir partiya boʻyicha “taʼsir qilmadi” yoki qadoq shikoyatlari toʻplansa — sifatsiz yoki qalbaki partiya signali. Laboratoriya namunasi uchun.</p>
        {batches.length === 0 ? <p className="text-sm text-gray-500">Hozircha signal yoʻq.</p> : (
          <ul className="space-y-2">
            {batches.slice(0, 8).map((b) => (
              <li key={`${b.drug}-${b.batch}`} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-gray-100 p-3 text-sm">
                <span><b>{b.drug}</b> · partiya <code>{b.batch}</code> — {b.reports} ta shikoyat ({b.quality_reports} ta sifat){b.regions.length ? ` · ${b.regions.join(", ")}` : ""}</span>
                <span className={`rounded-full px-2 py-0.5 text-xs font-bold ${b.level === "yuqori" ? "bg-red-100 text-red-800" : b.level === "oʻrta" ? "bg-amber-100 text-amber-800" : "bg-gray-100 text-gray-600"}`}>{b.level}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-2xl border border-gray-200 bg-white p-5">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-semibold">Tekshirish navbati</h2>
          <div className="flex rounded-lg bg-slate-100 p-0.5 text-xs font-semibold">
            {([["ai", "AI bahosi boʻyicha"], ["new", "Yangilari"]] as const).map(([k, label]) => (
              <button key={k} onClick={() => setSort(k)}
                className={`rounded-md px-3 py-1.5 ${sort === k ? "bg-white shadow-sm" : "text-slate-500"}`}>{label}</button>
            ))}
          </div>
        </div>
        <p className="mb-2 text-xs text-gray-500">AI bahosi — modelimiz hisoblagan qalbaki boʻlish ehtimoli. Qoidalar “joyida” degan, lekin AI shubha qilgan skanlar ham shu yerda. Tasdiqlash/rad etish modelni oʻrgatadi.</p>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead className="text-left text-gray-500">
              <tr>
                <th className="px-2 py-1 font-medium">AI</th>
                <th className="px-2 py-1 font-medium">Vaqt</th>
                <th className="px-2 py-1 font-medium">Natija</th>
                <th className="px-2 py-1 font-medium">Sabab</th>
                <th className="px-2 py-1 font-medium">Dorixona / hudud</th>
                <th className="px-2 py-1 font-medium">Dori, seriya</th>
              </tr>
            </thead>
            <tbody>
              {alerts.slice(0, 25).map((a) => (
                <tr key={a.scan_id} className="border-t border-gray-50 align-top">
                  <td className="px-2 py-2">
                    {a.ml_score != null ? (
                      <span className={`inline-block min-w-[2.5rem] rounded-full px-2 py-0.5 text-center text-xs font-bold ${a.ml_score >= 50 ? "bg-red-100 text-red-800" : a.ml_score >= 20 ? "bg-amber-100 text-amber-800" : "bg-slate-100 text-slate-600"}`}>{a.ml_score}</span>
                    ) : <span className="text-xs text-gray-400">—</span>}
                  </td>
                  <td className="whitespace-nowrap px-2 py-2 text-gray-600">{fmtDateTime(a.at)}</td>
                  <td className="px-2 py-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${a.verdict === "danger" ? "bg-red-100 text-red-800" : a.verdict === "warning" ? "bg-amber-100 text-amber-800" : "bg-indigo-100 text-indigo-800"}`}>
                      {a.verdict === "danger" ? "xavfli" : a.verdict === "warning" ? "diqqat" : "AI shubhasi"}
                    </span>
                    {a.reported && <div className="mt-1 text-xs font-medium text-red-700">xaridor xabar berdi{a.report_reason ? `: ${a.report_reason}` : ""}</div>}
                    {a.report_status === "tasdiqlandi" && <div className="mt-1 text-xs font-bold text-green-700">✓ tasdiqlandi, ball berildi</div>}
                    {a.report_status === "rad_etildi" && <div className="mt-1 text-xs text-gray-500">rad etildi</div>}
                    {(a.verdict === "danger" || a.reported || (a.ml_score ?? 0) >= 50) && !["tasdiqlandi", "rad_etildi"].includes(a.report_status) && (
                      <div className="mt-1 flex gap-1">
                        <button onClick={() => resolve(a.scan_id, true)} className="rounded bg-green-600 px-1.5 py-0.5 text-[11px] font-bold text-white">Tasdiqlash</button>
                        <button onClick={() => resolve(a.scan_id, false)} className="rounded bg-gray-200 px-1.5 py-0.5 text-[11px] font-bold">Rad</button>
                      </div>
                    )}
                  </td>
                  <td className="px-2 py-2">
                    {a.reasons.join("; ") || (a.ml_score != null && a.ml_score >= 50 ? "Qoidalar muammo topmadi, AI modeli shubha qildi" : "")}
                    {a.report_note && <div className="text-xs italic text-gray-500">“{a.report_note}”</div>}
                  </td>
                  <td className="px-2 py-2">{a.pharmacy || "—"}{a.region ? `, ${a.region}` : ""}</td>
                  <td className="px-2 py-2">
                    {a.drug} <span className="font-mono text-xs text-gray-500">{a.serial}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
