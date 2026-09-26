"use client";

import { useState } from "react";
import { api } from "@/lib/api";

/** Reestrda yoʻq mahsulot bazaga qoʻshildi — xaridor nomini yozib qoʻyishi mumkin. */
export function NewProductCard({ p }: { p: { gtin: string; name: string; scans: number; is_new: boolean; has_location: boolean } }) {
  const [name, setName] = useState(p.name);
  const [saved, setSaved] = useState(!!p.name);
  const [busy, setBusy] = useState(false);

  async function save() {
    if (name.trim().length < 2) return;
    setBusy(true);
    try {
      const r = await api.nameProduct(p.gtin, name.trim());
      setName(r.name);
      setSaved(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card border-violet-200 bg-violet-50/60">
      <div className="flex items-center gap-3">
        <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-violet-100 text-lg">🆕</div>
        <div className="flex-1">
          <div className="font-bold">Qutidagi dori nomi</div>
        </div>
      </div>
      {saved ? (
        <p className="mt-3 text-sm"><b>Nomi:</b> {name}</p>
      ) : (
        <div className="mt-3 flex gap-2">
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Qutidagi dori nomi (ixtiyoriy)" maxLength={80}
            className="min-w-0 flex-1 rounded-xl border border-slate-200 bg-white px-3 py-2.5 outline-none focus:border-violet-500" />
          <button onClick={save} disabled={busy || name.trim().length < 2}
            className="rounded-xl bg-violet-600 px-4 font-bold text-white disabled:opacity-40">Saqlash</button>
        </div>
      )}
    </div>
  );
}
