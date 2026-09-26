"use client";

import { useState } from "react";
import { api, ExplainResponse } from "@/lib/api";

const SUGGESTED = [
  "Bu dori sifatli ishlab chiqarilganmi?",
  "Originaldan farqi bormi?",
  "Qalbaki emasligini qanday bilaman?",
  "Kuniga necha tabletka ichish kerak?",
];

export function AskAI({ drugId }: { drugId: number }) {
  const [q, setQ] = useState("");
  const [res, setRes] = useState<ExplainResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function ask(question: string) {
    if (!question.trim()) return;
    setQ(question);
    setBusy(true);
    setError("");
    try {
      setRes(await api.explain(drugId, question));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {SUGGESTED.map((s) => (
          <button key={s} onClick={() => ask(s)} className="rounded-full bg-gray-50 px-3 py-1 text-sm ring-1 ring-gray-200 hover:ring-brand-500">
            {s}
          </button>
        ))}
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask(q);
        }}
        className="flex gap-2"
      >
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Savolingizni yozing…"
          className="min-w-0 flex-1 rounded-lg border border-gray-300 px-3 py-2 outline-none focus:border-brand-500"
        />
        <button disabled={busy} className="rounded-lg bg-brand-500 px-4 py-2 font-medium text-white hover:bg-brand-600 disabled:opacity-50">
          {busy ? "…" : "Soʻrash"}
        </button>
      </form>
      {error && <p className="text-sm text-red-700">{error}</p>}
      {res && (
        <div className={`rounded-lg p-4 text-sm ${res.blocked ? "bg-amber-50 text-amber-900" : "bg-brand-50 text-gray-800"}`}>
          <p className="whitespace-pre-line">{res.answer}</p>
          <p className="mt-2 text-xs text-gray-500">
            {res.blocked
              ? "Xavfsizlik filtri: tibbiy maslahat berilmaydi."
              : res.ai_used
                ? "AI javobi faqat yuqoridagi faktlar asosida yozildi. Raqamlar kartadagi manbalarga ishora qiladi."
                : "AI kaliti ulanmagan: javob faktlardan avtomatik yigʻildi."}
          </p>
        </div>
      )}
    </div>
  );
}
