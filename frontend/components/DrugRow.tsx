import Link from "next/link";
import { DrugBrief, som } from "@/lib/api";

export function LocalBadge({ local }: { local: boolean }) {
  return local ? (
    <span className="rounded-full bg-brand-100 px-2 py-0.5 text-xs font-medium text-brand-700">Mahalliy</span>
  ) : (
    <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">Import</span>
  );
}

export function DrugRow({ d }: { d: DrugBrief }) {
  return (
    <Link
      href={`/drug/${d.id}`}
      className="flex items-center justify-between gap-4 rounded-xl border border-gray-200 bg-white p-4 transition hover:border-brand-500 hover:shadow-sm"
    >
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-semibold">{d.trade_name}</span>
          <LocalBadge local={d.manufacturer.is_local} />
        </div>
        <div className="mt-0.5 text-sm text-gray-600">
          {d.inn} {d.strength}, {d.form} · {d.manufacturer.name}, {d.manufacturer.country}
        </div>
      </div>
      <div className="shrink-0 text-right">
        <div className="font-semibold">{som(d.price_uzs)}</div>
        <div className="text-xs text-gray-500">{d.pack_size}</div>
      </div>
    </Link>
  );
}
