"use client";

import { useEffect, useRef, useState } from "react";
import type { PackResult } from "@/lib/packnet";
import { checkPackaging, loadPackNet } from "@/lib/packnetClient";

type Sample = { file: string; gtin: string; name: string; label: string; truth: "asl" | "qalbaki" | "boshqa" };

const BADGE: Record<PackResult["verdict"], string> = {
  asl: "bg-emerald-100 text-emerald-800", farq: "bg-red-100 text-red-800",
  boshqa: "bg-amber-100 text-amber-900", tanilmadi: "bg-slate-100 text-slate-600",
};

/** PackNet ni brauzerda sinash: demo quti suratlari yoki oʻzingizning suratingiz. */
export function PackNetDemo() {
  const [samples, setSamples] = useState<Sample[]>([]);
  const [picked, setPicked] = useState<string | null>(null);
  const [res, setRes] = useState<PackResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(false);
  const file = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetch("/demo-qutilar/samples.json").then((r) => r.json()).then(setSamples).catch(() => {});
    loadPackNet().then(() => setReady(true)).catch(() => {});
  }, []);

  async function run(src: Blob | string, gtin?: string) {
    setBusy(true);
    setRes(null);
    try {
      const blob = typeof src === "string" ? await (await fetch(src)).blob() : src;
      setPicked(typeof src === "string" ? src : URL.createObjectURL(src));
      setRes(await checkPackaging(blob, gtin));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-2xl border border-violet-200 bg-white p-5">
      <h2 className="font-semibold">📦 Qadoq modelini sinab koʻring</h2>
      <p className="text-sm text-slate-600">Suratni bosing — model shu brauzerda ishlaydi, surat hech qayerga yuborilmaydi.</p>
      <div className="mt-3 grid grid-cols-4 gap-2 sm:grid-cols-8">
        {samples.map((s) => (
          <button key={s.file} onClick={() => run(`/demo-qutilar/${s.file}`, s.gtin)} disabled={!ready || busy}
            className={`overflow-hidden rounded-lg border-2 text-left ${picked?.endsWith(s.file) ? "border-violet-500" : "border-transparent"}`}>
            <img src={`/demo-qutilar/${s.file}`} alt={s.label} className="aspect-square w-full object-cover" />
            <div className="truncate px-1 py-0.5 text-[10px] text-slate-500">{s.label}</div>
          </button>
        ))}
      </div>
      <input ref={file} type="file" accept="image/*" className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ""; if (f) run(f); }} />
      <button onClick={() => file.current?.click()} disabled={!ready || busy}
        className="mt-3 rounded-lg bg-violet-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50">
        {ready ? "Oʻz suratingizni yuklash" : "Model yuklanmoqda…"}
      </button>
      {res && (
        <div className="mt-4 flex gap-4 rounded-xl bg-slate-50 p-3">
          {picked && <img src={picked} alt="" className="h-24 w-24 rounded-lg object-cover" />}
          <div className="flex-1 text-sm">
            <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${BADGE[res.verdict]}`}>{res.title}</span>
            <p className="mt-2 text-slate-700">{res.text}</p>
            <p className="mt-1 text-xs text-slate-500">
              Oʻxshash qadoq: {res.product.name} ({Math.round(res.product.prob * 100)}%) · farq ehtimoli {Math.round(res.fake_prob * 100)}% · {res.ms} ms
            </p>
          </div>
        </div>
      )}
    </section>
  );
}
