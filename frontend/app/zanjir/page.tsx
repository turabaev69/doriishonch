"use client";

import { useEffect, useState } from "react";
import { api, ChainStatus, fmtDateTime, KIND_LABEL, LedgerEntry } from "@/lib/api";

export default function Ledger() {
  const [status, setStatus] = useState<ChainStatus | null>(null);
  const [checking, setChecking] = useState(false);
  const [blocks, setBlocks] = useState<LedgerEntry[]>([]);
  const [gtin, setGtin] = useState("");
  const [serial, setSerial] = useState("");
  const [found, setFound] = useState<LedgerEntry[] | null>(null);
  const [error, setError] = useState("");

  async function verify() {
    setChecking(true);
    try {
      setStatus(await api.ledgerVerify());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setChecking(false);
    }
  }

  useEffect(() => {
    verify();
    api.ledgerLatest(40).then(setBlocks).catch((e) => setError(e.message));
  }, []);

  async function search(e: React.FormEvent) {
    e.preventDefault();
    try {
      setFound(await api.ledgerCode(gtin.trim(), serial.trim()));
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">DoriIshonch zanjiri</h1>
        <p className="max-w-3xl text-sm text-gray-600">
          Har bir xaridor skanerlashi zanjirga blok boʻlib yoziladi. Blok oʻzidan oldingi blokning hashini (SHA-256) saqlaydi,
          shuning uchun birorta yozuvni oʻzgartirish yoki oʻchirish butun zanjirni buzadi va darhol aniqlanadi. Blokda ism,
          telefon yoki joylashuv yoʻq: faqat quti kodi, dorixona va vaqt.
        </p>
      </div>
      {error && <p className="rounded-lg bg-red-50 p-3 text-red-700">{error}</p>}

      <section className={`rounded-2xl p-5 ${status ? (status.ok ? "bg-emerald-50" : "bg-red-50") : "bg-white"} border border-gray-200`}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className={`text-lg font-semibold ${status && !status.ok ? "text-red-800" : "text-emerald-800"}`}>
              {!status ? "Tekshirilmoqda…" : status.ok ? `✓ Zanjir butun: ${status.blocks} blok tekshirildi` : `✕ Zanjir buzilgan: blok #${status.broken_at}`}
            </div>
            {status && !status.ok && <div className="text-sm text-red-800">{status.reason}</div>}
            {status?.ok && <div className="mt-1 break-all font-mono text-xs text-gray-500">oxirgi hash: {status.last_hash}</div>}
          </div>
          <button onClick={verify} disabled={checking} className="rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
            Qayta tekshirish
          </button>
        </div>
      </section>

      <form onSubmit={search} className="grid gap-2 rounded-2xl border border-gray-200 bg-white p-5 sm:grid-cols-[1fr_1fr_auto]">
        <input value={gtin} onChange={(e) => setGtin(e.target.value)} placeholder="GTIN" className="rounded-lg border border-gray-300 px-3 py-2" />
        <input value={serial} onChange={(e) => setSerial(e.target.value)} placeholder="Seriya raqami" className="rounded-lg border border-gray-300 px-3 py-2" />
        <button className="rounded-lg bg-brand-500 px-4 py-2 font-medium text-white">Quti tarixini koʻrish</button>
        {found && (
          <div className="sm:col-span-3">
            {found.length === 0 ? <p className="text-sm text-gray-600">Bu quti zanjirda yoʻq.</p> : <Blocks list={found} />}
          </div>
        )}
      </form>

      <section className="rounded-2xl border border-gray-200 bg-white p-5">
        <h2 className="mb-3 font-semibold">Soʻnggi bloklar</h2>
        <Blocks list={blocks} />
      </section>
    </div>
  );
}

function Blocks({ list }: { list: LedgerEntry[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[720px] text-sm">
        <thead className="text-left text-gray-500">
          <tr>
            <th className="px-2 py-1 font-medium">#</th>
            <th className="px-2 py-1 font-medium">Vaqt</th>
            <th className="px-2 py-1 font-medium">Hodisa</th>
            <th className="px-2 py-1 font-medium">Quti</th>
            <th className="px-2 py-1 font-medium">Joy</th>
            <th className="px-2 py-1 font-medium">Hash / oldingi hash</th>
          </tr>
        </thead>
        <tbody>
          {list.map((b) => (
            <tr key={b.index} className="border-t border-gray-50 align-top">
              <td className="px-2 py-1.5 font-mono">{b.index}</td>
              <td className="whitespace-nowrap px-2 py-1.5 text-gray-600">{fmtDateTime(b.created_at)}</td>
              <td className="px-2 py-1.5">
                {KIND_LABEL[b.kind] ?? b.kind}
                {b.is_demo && <span className="ml-1 rounded bg-amber-50 px-1 text-[10px] text-amber-800">demo</span>}
              </td>
              <td className="px-2 py-1.5 font-mono text-xs">{b.serial}</td>
              <td className="px-2 py-1.5 text-gray-600">{[b.pharmacy, b.region].filter(Boolean).join(", ")}</td>
              <td className="px-2 py-1.5 font-mono text-[10px] text-gray-500">
                {b.hash.slice(0, 16)}…
                <br />
                <span className="text-gray-400">← {b.prev_hash.slice(0, 16)}…</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
