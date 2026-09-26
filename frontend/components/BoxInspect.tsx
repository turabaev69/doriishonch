"use client";

import { useRef, useState } from "react";
import { api, BoxInspection } from "@/lib/api";
import type { PackResult } from "@/lib/packnet";
import { checkPackaging } from "@/lib/packnetClient";

const ICON: Record<string, string> = { ok: "✓", warning: "!", unknown: "?" };
const CLS: Record<string, string> = {
  ok: "bg-emerald-100 text-emerald-700",
  warning: "bg-amber-100 text-amber-800",
  unknown: "bg-gray-100 text-gray-600",
};
export const PACK_STATUS: Record<PackResult["verdict"], "ok" | "warning" | "unknown"> = {
  asl: "ok", farq: "warning", boshqa: "warning", tanilmadi: "unknown",
};

/** Qutini suratdan tekshirish: avval telefondagi AI (internetsiz, surat yuborilmaydi), keyin server (yozuvlar). */
export function BoxInspect({ gtin, serial }: { gtin?: string; serial?: string }) {
  const ref = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [local, setLocal] = useState<PackResult | null>(null);
  const [server, setServer] = useState<BoxInspection | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState("");

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    setBusy(true);
    setError("");
    setLocal(null);
    setServer(null);
    setPreview(URL.createObjectURL(f));
    let onDevice: PackResult | null = null;
    try {
      onDevice = await checkPackaging(f, gtin);
      setLocal(onDevice);
    } catch {
      setError("Qurilmadagi model ishlamadi. Serverda tekshirilmoqda…");
    }
    try {
      const form = new FormData();
      form.append("file", f);
      if (gtin) form.append("gtin", gtin);
      if (serial) form.append("serial", serial);
      const res = await api.inspectBox(form);
      if (res.ai_used) setServer(res);
      else if (!onDevice && res.model) setLocal(res.model);
    } catch {
      /* server ixtiyoriy: telefondagi natija yetarli */
    } finally {
      setBusy(false);
    }
  }

  const extra = server?.checks.filter((c) => c.key !== "packnet") ?? [];

  return (
    <div className="card">
      <div className="flex items-center gap-3">
        <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-violet-50 text-lg">📸</div>
        <div className="flex-1">
          <div className="font-semibold">Qutini suratdan tekshirish</div>
          <div className="text-xs text-slate-500">AI qadoqni asl dizayn bilan solishtiradi</div>
        </div>
      </div>
      <input ref={ref} type="file" accept="image/*" capture="environment" onChange={onFile} className="hidden" />
      <button onClick={() => ref.current?.click()} disabled={busy}
        className="mt-3 w-full rounded-xl bg-violet-600 px-4 py-3 text-sm font-semibold text-white disabled:opacity-50">
        {busy ? "Tekshirilmoqda…" : local ? "Yana suratga olish" : "Qutini suratga olish"}
      </button>
      {error && <p className="mt-2 text-sm text-amber-700">{error}</p>}

      {local && (
        <div className="mt-3 flex gap-3">
          {preview && <img src={preview} alt="" className="h-20 w-20 shrink-0 rounded-lg object-cover" />}
          <div className="flex-1">
            <div className={`inline-flex items-center gap-2 rounded-lg px-2.5 py-1 text-sm font-semibold ${CLS[PACK_STATUS[local.verdict]]}`}>
              {ICON[PACK_STATUS[local.verdict]]} {local.title}
            </div>
            <p className="mt-1 text-sm text-slate-700">{local.text}</p>
            <p className="mt-1 text-xs text-slate-400">
              {local.on_device ? `Telefoningizda tekshirildi${local.ms ? ` (${local.ms} ms)` : ""}, surat hech qayerga yuborilmadi` : "Serverda tekshirildi"}
            </p>
          </div>
        </div>
      )}

      {extra.length > 0 && (
        <ul className="mt-3 space-y-1 border-t border-slate-100 pt-3">
          {extra.map((c, i) => (
            <li key={i} className="flex gap-2 text-sm">
              <span className={`grid h-5 w-5 shrink-0 place-items-center rounded-full text-xs font-bold ${CLS[c.status] ?? CLS.unknown}`}>{ICON[c.status] ?? "?"}</span>
              <span><b>{c.title}:</b> {c.text}</span>
            </li>
          ))}
        </ul>
      )}
      {(local || server) && (
        <p className="mt-2 text-xs text-slate-400">Bu AI signali, yakuniy xulosa emas. Shubha boʻlsa, dorini olmang va xabar bering.</p>
      )}
    </div>
  );
}
