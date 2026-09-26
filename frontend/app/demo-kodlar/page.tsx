"use client";

import { useEffect, useState } from "react";
import { api, DemoCode, Participant, VerifyResponse } from "@/lib/api";
import { Barcode } from "@/components/Barcode";

const EXPECTED: Record<string, string> = {
  ok: "bg-emerald-100 text-emerald-800",
  warning: "bg-amber-100 text-amber-800",
  danger: "bg-red-100 text-red-800",
};
const EXPECTED_LABEL: Record<string, string> = { ok: "Yashil", warning: "Sariq", danger: "Qizil" };

export default function DemoCodes() {
  const [codes, setCodes] = useState<DemoCode[]>([]);
  const [origin, setOrigin] = useState("");
  const [results, setResults] = useState<Record<string, VerifyResponse["verdict"]>>({});
  const [error, setError] = useState("");
  const [pharmacies, setPharmacies] = useState<Participant[]>([]);

  useEffect(() => {
    setOrigin(window.location.origin);
    api.demoCodes().then(setCodes).catch((e) => setError(e.message));
    api.pharmacies().then(rows => setPharmacies(rows.filter(pharmacy => !pharmacy.is_demo).slice(0, 2))).catch(() => {});
  }, []);

  async function check(c: DemoCode) {
    // Har bir stsenariy oʻz "qurilmasi" bilan: takroriy bosishlar boshqa xaridor deb hisoblanmaydi
    const r = await api.verify({ code: c.code, mode: c.mode, pharmacy_id: c.pharmacy_id, device_id: `demo-${c.key}` });
    setResults((x) => ({ ...x, [c.key]: r.verdict }));
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Demo kodlar</h1>
        <p className="text-gray-600">
          Har bir kod bitta vaziyatni koʻrsatadi. Telefonda <b>Tekshirish</b> sahifasini oching va ekrandagi kodni skanerlang
          (yoki chop eting). Dorixonani va rejimni kod ostidagi yozuvga qarab tanlang.
        </p>
      </div>
      {error && <p className="rounded-lg bg-red-50 p-3 text-red-700">{error}</p>}

      <section className="rounded-2xl border border-gray-200 bg-white p-5">
        <h2 className="font-semibold">Dorixona kirishidagi QR</h2>
        <p className="mb-3 text-sm text-gray-600">
          Xaridor dorixonaga kirganda shu QR ni skanerlaydi: tekshirish sahifasi dorixona tanlangan holda ochiladi.
        </p>
        <div className="flex flex-wrap items-end gap-6">
          {origin &&
            pharmacies.map(({ id, name }) => (
              <div key={id} className="text-center">
                <Barcode type="qrcode" text={`${origin}/?dorixona=${id}`} scale={3} />
                <div className="mt-1 text-xs text-gray-600">{name}</div>
              </div>
            ))}
        </div>
      </section>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {codes.map((c) => (
          <div key={c.key} className="flex flex-col rounded-2xl border border-gray-200 bg-white p-4">
            <div className="flex items-start justify-between gap-2">
              <span className="font-medium">{c.title}</span>
              <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${EXPECTED[c.expected]}`}>
                {EXPECTED_LABEL[c.expected]}
              </span>
            </div>
            <div className="my-3 grid place-items-center">
              <Barcode type="gs1datamatrix" text={c.code_display} />
            </div>
            <div className="text-xs text-gray-600">
              {c.trade_name} · rejim: {c.mode === "before" ? "sotib olishdan oldin" : "sotib oldim"}
              {c.pharmacy_name && <> · dorixona: {c.pharmacy_name}</>}
            </div>
            <div className="mt-1 break-all font-mono text-[10px] text-gray-400">{c.code_display}</div>
            <button onClick={() => check(c)} className="mt-3 self-start rounded-lg bg-gray-900 px-3 py-1.5 text-sm text-white">
              Shu yerda tekshirish
            </button>
            {results[c.key] && (
              <div className="mt-2 text-sm">
                Natija: <b>{EXPECTED_LABEL[results[c.key]] ?? results[c.key]}</b>{" "}
                {results[c.key] === c.expected ? "✓ kutilgandek" : "✕ kutilmagan"}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
