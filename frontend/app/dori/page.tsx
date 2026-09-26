"use client";

import { Icon } from "@/components/Icon";

import { useEffect, useRef, useState } from "react";
import { api, DrugBrief, ScanResponse } from "@/lib/api";
import { DrugRow } from "@/components/DrugRow";

const EXAMPLES = ["Norvadin", "Glucoren", "Lozarex", "omeprazol", "atorvastatin"];

export default function DrugSearch() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<DrugBrief[] | null>(null);
  const [scan, setScan] = useState<ScanResponse | null>(null);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (q.trim().length < 2) {
      setResults(null);
      return;
    }
    const t = setTimeout(() => {
      api.search(q).then((r) => setResults(r.results)).catch((e) => setError(e.message));
    }, 250);
    return () => clearTimeout(t);
  }, [q]);

  async function sendScan(form: FormData) {
    setBusy(true);
    setError("");
    setScan(null);
    try {
      setScan(await api.scan(form));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    const form = new FormData();
    form.append("file", f);
    sendScan(form);
    e.target.value = "";
  }

  function onCode(e: React.FormEvent) {
    e.preventDefault();
    if (!code.trim()) return;
    const form = new FormData();
    form.append("code", code.trim());
    sendScan(form);
  }

  return (
    <div className="search-shell space-y-7">
      <section className="page-heading">
        <div><span className="eyebrow mb-2"><Icon name="search" size={17} />Kerakli maʼlumot, bir joyda</span><h1>Doringiz haqida bilib oling.</h1><p>Dori nomini yozing. Tarkibi, ishlab chiqaruvchisi va mavjud maʼlumotlarni koʻrsatamiz.</p></div>
      </section>

      <section className="space-y-3">
        <label className="search-field"><Icon name="search" size={24} /><input
          aria-label="Dori nomini qidirish"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Dori nomi, masalan: amlodipin"
        /></label>
        <div className="flex flex-wrap gap-2 text-sm">
          <span className="text-gray-500">Misollar:</span>
          {EXAMPLES.map((e) => (
            <button key={e} onClick={() => setQ(e)} className="rounded-full bg-white px-3 py-1 ring-1 ring-gray-200 hover:ring-brand-500">
              {e}
            </button>
          ))}
        </div>
      </section>

      {results && (
        <section className="space-y-2">
          {results.length === 0 ? (
            <p className="text-gray-600">Hech narsa topilmadi. Nomni boshqacha yozib koʻring.</p>
          ) : (
            results.map((d) => <DrugRow key={d.id} d={d} />)
          )}
        </section>
      )}

      <section className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="card">
          <span className="step-symbol mb-4"><Icon name="camera" /></span><h2 className="font-bold">Surat orqali topish</h2>
          <p className="mt-1 text-sm text-gray-600">AI qadoqdagi nom, doza va shaklni oʻqib, dorini topadi.</p>
          <input ref={fileRef} type="file" accept="image/*" capture="environment" onChange={onFile} className="hidden" />
          <button
            onClick={() => fileRef.current?.click()}
            disabled={busy}
            className="primary-button mt-4"
          >
            {busy ? "Tahlil qilinmoqda…" : "Surat yuklash"}
          </button>
        </div>
        <form onSubmit={onCode} className="card">
          <span className="step-symbol mb-4"><Icon name="keyboard" /></span><h2 className="font-bold">Kod orqali topish</h2>
          <p className="mt-1 text-sm text-gray-600">Kvadrat kod ostidagi yozuvni yoki (01) dan keyingi 14 ta raqamni kiriting.</p>
          <div className="mt-4 flex flex-col gap-2 sm:flex-row">
            <input
              aria-label="Dori qutisidagi kod"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="0104780000007919…"
              className="min-w-0 flex-1 rounded-lg border border-gray-300 px-3 py-2 outline-none focus:border-brand-500"
            />
            <button disabled={busy || !code.trim()} className="primary-button">
              Tekshirish
            </button>
          </div>
        </form>
      </section>

      {error && <p role="alert" className="error-notice">{error}</p>}

      {scan && (
        <section className="space-y-2">
          <h2 className="font-semibold">Skanerlash natijasi</h2>
          {Object.keys(scan.extracted).length > 0 && (
            <p className="text-sm text-gray-600">
              Aniqlandi:{" "}
              {Object.entries(scan.extracted)
                .filter(([, v]) => v)
                .map(([k, v]) => `${k}: ${v}`)
                .join(" · ")}
            </p>
          )}
          {scan.note && <p className="text-sm text-amber-800">{scan.note}</p>}
          {scan.matches.map((d) => (
            <DrugRow key={d.id} d={d} />
          ))}
        </section>
      )}
    </div>
  );
}
