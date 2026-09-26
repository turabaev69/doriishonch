import { Fact } from "@/lib/api";

const STYLE: Record<Fact["status"], { icon: string; cls: string; word: string }> = {
  ok: { icon: "✓", cls: "bg-emerald-100 text-emerald-700", word: "Tasdiqlangan" },
  warn: { icon: "!", cls: "bg-amber-100 text-amber-800", word: "Diqqat" },
  missing: { icon: "–", cls: "bg-gray-100 text-gray-500", word: "Maʼlumot yoʻq" },
  info: { icon: "i", cls: "bg-sky-100 text-sky-700", word: "Maʼlumot" },
};

function fmtDate(s: string | null) {
  if (!s) return "";
  const [y, m, d] = s.split("-");
  return `${d}.${m}.${y}`;
}

export function FactList({ facts }: { facts: Fact[] }) {
  return (
    <ul className="divide-y divide-gray-100">
      {facts.map((f, i) => {
        const s = STYLE[f.status];
        return (
          <li key={i} className="flex gap-3 py-3">
            <span className={`mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full text-sm font-bold ${s.cls}`} title={s.word}>
              {s.icon}
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs text-gray-400">[{i + 1}]</span>
                <span className="font-medium">{f.label}</span>
                {f.provided_by_manufacturer && (
                  <span className="rounded bg-sky-50 px-1.5 py-0.5 text-xs text-sky-700">ishlab chiqaruvchi taqdim etgan</span>
                )}
                {f.is_demo && <span className="rounded bg-amber-50 px-1.5 py-0.5 text-xs text-amber-800">demo</span>}
              </div>
              <p className="text-sm text-gray-700">{f.text}</p>
              {(f.source_url || f.updated_at) && (
                <p className="mt-0.5 text-xs text-gray-500">
                  {f.source_url && (
                    <a href={f.source_url} target="_blank" rel="noreferrer" className="underline hover:text-brand-700">
                      Manba
                    </a>
                  )}
                  {f.updated_at && <> · yangilangan {fmtDate(f.updated_at)}</>}
                </p>
              )}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
