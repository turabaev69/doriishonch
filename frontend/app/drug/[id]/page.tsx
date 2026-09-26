"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AnalogsResponse, api, som, TrustCard } from "@/lib/api";
import { FactList } from "@/components/FactList";
import { AskAI } from "@/components/AskAI";
import { LocalBadge } from "@/components/DrugRow";

export default function DrugPage() {
  const { id } = useParams<{ id: string }>();
  const drugId = Number(id);
  const [card, setCard] = useState<TrustCard | null>(null);
  const [analogs, setAnalogs] = useState<AnalogsResponse | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setCard(null);
    setAnalogs(null);
    Promise.all([api.card(drugId), api.analogs(drugId)])
      .then(([c, a]) => {
        setCard(c);
        setAnalogs(a);
      })
      .catch((e) => setError(e.message));
  }, [drugId]);

  if (error) return <p className="rounded-lg bg-red-50 p-3 text-red-700">{error}</p>;
  if (!card || !analogs) return <p className="text-gray-500">Yuklanmoqda…</p>;
  const d = card.drug;

  return (
    <div className="space-y-6">
      <Link href="/dori" className="text-sm text-gray-500 hover:text-brand-700">← Qidiruvga qaytish</Link>

      <section className="rounded-2xl border border-gray-200 bg-white p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-bold">{d.trade_name}</h1>
              <LocalBadge local={d.manufacturer.is_local} />
            </div>
            <p className="mt-1 text-gray-600">
              {d.inn} {d.strength}, {d.form} · {d.atc_group}
            </p>
            <p className="text-sm text-gray-500">
              {d.manufacturer.name}, {d.manufacturer.country}
            </p>
          </div>
          <div className="text-right">
            <div className="text-xl font-semibold">{som(d.price_uzs)}</div>
            <div className="text-xs text-gray-500">{d.pack_size}</div>
          </div>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-5">
        <section className="rounded-2xl border border-gray-200 bg-white p-6 lg:col-span-3">
          <h2 className="text-lg font-semibold">Rasmiy maʼlumotlar</h2>
          <p className="text-sm text-gray-500">Faqat tekshiriladigan faktlar. Ball yoki reyting qoʻyilmaydi.</p>
          <FactList facts={card.facts} />
          <p className="mt-2 rounded-lg bg-gray-50 p-3 text-xs text-gray-600">{card.disclaimer}</p>
        </section>

        <section className="rounded-2xl border border-gray-200 bg-white p-6 lg:col-span-2">
          <h2 className="text-lg font-semibold">AI dan soʻrang</h2>
          <p className="mb-3 text-sm text-gray-500">Javob faqat kartadagi faktlarga asoslanadi.</p>
          <AskAI drugId={d.id} />
        </section>
      </div>

      <section className="rounded-2xl border border-gray-200 bg-white p-6">
        <h2 className="text-lg font-semibold">Analoglar</h2>
        <p className="mb-4 text-sm text-gray-500">{analogs.note}</p>
        {analogs.analogs.length === 0 ? (
          <p className="text-sm text-gray-600">Bazada mos analog yoʻq.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-sm">
              <thead className="text-left text-gray-500">
                <tr className="border-b border-gray-100">
                  <th className="px-2 py-2 font-medium">Preparat</th>
                  <th className="px-2 py-2 font-medium">Ishlab chiqaruvchi</th>
                  <th className="px-2 py-2 text-right font-medium">Narx</th>
                  <th className="px-2 py-2 text-right font-medium">Farq</th>
                  <th className="px-2 py-2 text-center font-medium">Amaldagi GMP</th>
                  <th className="px-2 py-2 text-center font-medium">Sifat ogohlantirishi</th>
                  <th className="px-2 py-2 text-center font-medium">Ekvivalentlik hujjati</th>
                </tr>
              </thead>
              <tbody>
                {analogs.analogs.map((a) => (
                  <tr key={a.drug.id} className="border-b border-gray-50">
                    <td className="px-2 py-2">
                      <Link href={`/drug/${a.drug.id}`} className="font-medium text-brand-700 hover:underline">
                        {a.drug.trade_name}
                      </Link>{" "}
                      <LocalBadge local={a.drug.manufacturer.is_local} />
                    </td>
                    <td className="px-2 py-2 text-gray-600">
                      {a.drug.manufacturer.name}, {a.drug.manufacturer.country}
                    </td>
                    <td className="whitespace-nowrap px-2 py-2 text-right">{som(a.drug.price_uzs)}</td>
                    <td className={`py-2 text-right ${a.price_diff_uzs < 0 ? "text-emerald-700" : "text-gray-600"}`}>
                      {a.price_diff_uzs > 0 ? "+" : ""}
                      {a.price_diff_pct}%
                    </td>
                    <td className="px-2 py-2 text-center">{a.has_valid_gmp ? "bor" : "bazada yoʻq"}</td>
                    <td className="px-2 py-2 text-center">{a.quality_alert_count ? `${a.quality_alert_count} ta` : "yoʻq"}</td>
                    <td className="px-2 py-2 text-center">{a.evidence_count ? `${a.evidence_count} ta` : "yoʻq"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
