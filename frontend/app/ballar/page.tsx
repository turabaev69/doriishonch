"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api, fmtDateTime, LeaderRow, Mission, RewardItem, Wallet } from "@/lib/api";
import { getDeviceId } from "@/lib/device";

const RULE_ICON: Record<string, string> = { scan: "🔳", pharmacy: "🏪", purchase: "🛒", mission: "🚩", catch: "🛡️", report: "📣", bounty: "🏆" };

export default function Page() {
  const [w, setW] = useState<Wallet | null>(null);
  const [missions, setMissions] = useState<Mission[]>([]);
  const [board, setBoard] = useState<LeaderRow[]>([]);
  const [items, setItems] = useState<RewardItem[]>([]);
  const [error, setError] = useState("");
  const [nick, setNick] = useState("");
  const [nickMsg, setNickMsg] = useState("");
  const [redeemed, setRedeemed] = useState("");

  const load = useCallback(async () => {
    try {
      const id = getDeviceId();
      const [a, b, c, d] = await Promise.all([api.wallet(id), api.missions(id), api.leaderboard(id), api.rewardCatalog()]);
      setW(a); setMissions(b); setBoard(c); setItems(d.items);
      setNick(a.has_nickname ? a.nickname : "");
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  async function saveNick(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api.nickname(getDeviceId(), nick);
      setNickMsg("✓ Saqlandi");
      load();
    } catch (err) {
      setNickMsg((err as Error).message);
    }
  }

  async function redeem(it: RewardItem) {
    if (!confirm(`${it.title}: ${it.points} ball sarflanadi. Davom etamizmi?`)) return;
    try {
      const r = await api.redeem(getDeviceId(), it.key);
      setRedeemed(`🎉 Kod: ${r.code} — ${r.note}`);
      load();
    } catch (err) {
      setRedeemed((err as Error).message);
    }
  }

  const top = board.filter((r) => r.rank <= 10 || r.me);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {error && <p className="rounded-2xl bg-red-50 p-4 text-sm text-red-700">{error}</p>}
      <section className="hero-grad relative overflow-hidden rounded-[2rem] p-6 text-white shadow-lg sm:p-8">
        <div className="pointer-events-none absolute -right-12 -top-12 h-48 w-48 rounded-full bg-white/10" />
        <div className="relative flex items-center justify-between">
          <span className="font-bold">{w?.nickname ?? "…"}</span>
          {w?.rank && <span className="rounded-full bg-white/20 px-3 py-1 text-sm font-bold">🏆 #{w.rank}</span>}
        </div>
        <div className="relative mt-3 flex items-end gap-2">
          <span className="text-5xl text-gold">★</span>
          <span className="text-6xl font-black tracking-tighter">{w?.points ?? 0}</span>
          <span className="mb-2 text-lg font-bold text-white/85">ball</span>
        </div>
        {w && (
          <>
            <div className="relative mt-2 font-semibold">
              {w.level.icon} {w.level.name}{w.level.next_name ? ` → ${w.level.next_name} (${w.level.next_min})` : " · eng yuqori daraja"}
            </div>
            <div className="relative mt-2 h-2.5 overflow-hidden rounded-full bg-white/25">
              <div className="h-full rounded-full bg-gold" style={{ width: `${Math.max(3, w.level.progress * 100)}%` }} />
            </div>
            <div className="relative mt-4 grid grid-cols-3 gap-2 text-center">
              {[["🔥", `${w.streak}`, "kun ketma-ket"], ["📅", `${w.today.earned}/${w.today.cap}`, "bugun"], ["⏳", `${w.pending}`, "kutilmoqda"]].map(([i, v, l]) => (
                <div key={l} className="rounded-2xl bg-white/15 p-3">
                  <div className="text-lg font-black">{i} {v}</div>
                  <div className="text-xs text-white/85">{l}</div>
                </div>
              ))}
            </div>
          </>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-extrabold">🚩 Haftalik missiyalar</h2>
        <p className="text-sm text-slate-600">Tekshiruvlar kam boʻlgan dorixonalarda skanerlang — soxta dorilarni birga topamiz. Har biri +30 ball.</p>
        <div className="grid gap-3 sm:grid-cols-2">
          {missions.map((m) => (
            <div key={m.id} className={`card ${m.done ? "opacity-70" : ""}`}>
              <div className="flex items-start justify-between gap-2">
                <div className="font-bold">{m.pharmacy}</div>
                {m.done
                  ? <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-bold text-green-700">✓ Bajarildi</span>
                  : <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs font-bold text-amber-700">★ +{m.points}</span>}
              </div>
              <div className="text-sm text-slate-500">{m.region}{m.address ? ` · ${m.address}` : ""}</div>
              <div className="mt-1 text-xs text-slate-400">Bu hafta {m.scanners_this_week} kishi tekshirdi</div>
              {!m.done && <Link href={`/?dorixona=${m.pharmacy_id}`} className="mt-2 inline-block text-sm font-bold text-brand-700">Shu dorixonada skanerlash →</Link>}
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-extrabold">Nishonlar</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {(w?.badges ?? []).map((b) => (
            <div key={b.key} className={`card p-4 text-center ${b.earned ? "" : "opacity-40 grayscale"}`}>
              <div className="text-3xl">{b.icon}</div>
              <div className="mt-1 font-bold">{b.title}</div>
              <div className="text-xs text-slate-500">{b.description}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-extrabold">Mukofotlar</h2>
        {redeemed && <p className="rounded-2xl bg-amber-50 p-4 text-sm font-medium text-amber-900">{redeemed}</p>}
        <div className="grid gap-3 sm:grid-cols-2">
          {items.map((it) => {
            const enough = (w?.points ?? 0) >= it.points;
            return (
              <div key={it.key} className="card flex items-center gap-4">
                <span className="grid h-14 w-14 shrink-0 place-items-center rounded-2xl bg-amber-50 text-3xl">{it.icon}</span>
                <div className="flex-1">
                  <div className="font-bold">{it.title}</div>
                  <div className="text-xs text-slate-500">{it.partner}</div>
                  {!enough && w && (
                    <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100">
                      <div className="h-full rounded-full bg-gold" style={{ width: `${(w.points / it.points) * 100}%` }} />
                    </div>
                  )}
                </div>
                <button disabled={!enough} onClick={() => redeem(it)}
                  className={`rounded-xl px-3 py-2 text-sm font-bold ${enough ? "gold-grad text-white shadow" : "bg-slate-100 text-slate-400"}`}>
                  ★ {it.points}
                </button>
              </div>
            );
          })}
        </div>
        {w && w.redemptions.length > 0 && (
          <div className="card text-sm">
            <div className="font-bold">Mening kodlarim</div>
            {w.redemptions.map((r) => <div key={r.code} className="mt-1">🎟 {r.title} — <code className="font-bold">{r.code}</code></div>)}
          </div>
        )}
      </section>

      <div className="grid gap-6 md:grid-cols-2">
        <section className="space-y-3">
          <h2 className="text-xl font-extrabold">Reyting · 30 kun</h2>
          <div className="card space-y-1 p-3">
            {top.map((r) => (
              <div key={`${r.rank}-${r.name}`} className={`flex items-center gap-3 rounded-xl px-2 py-2 ${r.me ? "bg-brand-50" : ""}`}>
                <span className="w-8 text-center text-lg font-extrabold text-slate-400">{r.rank <= 3 ? ["🥇", "🥈", "🥉"][r.rank - 1] : r.rank}</span>
                <span className="flex-1">
                  <span className="font-bold">{r.name}{r.me ? " (siz)" : ""}</span>
                  {r.region && <span className="block text-xs text-slate-400">{r.region}</span>}
                </span>
                <span className="font-extrabold text-brand-700">{r.points}</span>
              </div>
            ))}
          </div>
          <form onSubmit={saveNick} className="card flex flex-col gap-2 sm:flex-row sm:items-center">
            <input value={nick} onChange={(e) => setNick(e.target.value)} placeholder="Reyting uchun taxallus"
              className="min-w-0 flex-1 rounded-xl border border-slate-200 px-3 py-2 outline-none focus:border-brand-500" />
            <button className="rounded-xl bg-ink px-4 py-2 font-bold text-white">Saqlash</button>
            {nickMsg && <span className="text-xs text-slate-500">{nickMsg}</span>}
          </form>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-extrabold">Qanday ball olinadi</h2>
          <div className="card space-y-2">
            {(w?.rules ?? []).map((r) => (
              <div key={r.kind} className="flex items-center gap-3">
                <span className="text-xl">{RULE_ICON[r.kind] ?? "★"}</span>
                <span className="flex-1">
                  <span className="font-medium">{r.label}</span>
                  {["catch", "report", "bounty"].includes(r.kind) && <span className="block text-xs text-slate-400">inspektor tasdiqlagandan keyin</span>}
                </span>
                <span className="font-extrabold text-amber-600">+{r.points}</span>
              </div>
            ))}
          </div>
          <p className="text-xs text-slate-500">
            Adolat qoidalari: bitta quti uchun bir marta; kuniga {w?.today.cap ?? 150} balldan koʻp emas; bitta qutiga kuniga 3 kishidan
            koʻp ball olmaydi; soxta kod terib ball yigʻib boʻlmaydi — “shubhali quti” ballari faqat inspektor tasdigʻidan keyin.
          </p>
        </section>
      </div>

      {w && w.history.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-xl font-extrabold">Ball tarixi</h2>
          <div className="card divide-y divide-slate-100 p-3">
            {w.history.slice(0, 15).map((h) => (
              <div key={h.id} className="flex items-center justify-between gap-3 py-2 text-sm">
                <span><span className="font-medium">{h.note || h.label}</span> <span className="text-xs text-slate-400">· {h.label} · {fmtDateTime(h.at)}</span></span>
                <span className={`font-extrabold ${h.status === "pending" ? "text-slate-400" : h.status === "rejected" ? "text-red-600 line-through" : h.points < 0 ? "text-slate-700" : "text-green-600"}`}>
                  {h.status === "pending" ? "⏳ " : ""}{h.points > 0 ? "+" : ""}{h.points}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
