import type { AiRisk } from "@/lib/api";

const LEVEL: Record<AiRisk["level"], { label: string; bar: string; pill: string }> = {
  past: { label: "Past xavf", bar: "bg-emerald-500", pill: "bg-emerald-100 text-emerald-800" },
  "oʻrta": { label: "Oʻrtacha xavf", bar: "bg-amber-500", pill: "bg-amber-100 text-amber-900" },
  yuqori: { label: "Yuqori xavf", bar: "bg-red-500", pill: "bg-red-100 text-red-800" },
};

/** Oʻz modelimiz bahosi. Asosiy xulosa — yuqoridagi qoidalar; bu qoʻshimcha signal. */
export function AiRiskCard({ risk }: { risk: AiRisk }) {
  const l = LEVEL[risk.level] ?? LEVEL.past;
  return (
    <div className="card">
      <div className="flex items-center gap-3">
        <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-indigo-50 text-lg">🧠</div>
        <div className="flex-1">
          <div className="font-semibold">AI bahosi</div>
          <div className="text-xs text-slate-500">Minglab tekshiruvlardan oʻrgangan modelimiz</div>
        </div>
        <span className={`rounded-full px-3 py-1 text-sm font-bold ${l.pill}`}>{l.label}</span>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100" aria-label={`Xavf ${risk.score} / 100`}>
        <div className={`h-full rounded-full ${l.bar}`} style={{ width: `${Math.max(3, risk.score)}%` }} />
      </div>
      {risk.reasons.length > 0 && risk.level !== "past" && (
        <ul className="mt-3 space-y-1 text-sm">
          {risk.reasons.map((r) => (
            <li key={r.text} className="flex gap-2">
              <span className="text-slate-400">•</span>
              {r.text}
            </li>
          ))}
        </ul>
      )}
      <p className="mt-2 text-xs text-slate-400">Qoʻshimcha signal. Asosiy xulosa yuqorida.</p>
    </div>
  );
}
