"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, Insights, Manufacturer, som } from "@/lib/api";
import { getSession } from "@/lib/auth";

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4">
      <div className="text-sm text-gray-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
    </div>
  );
}

export default function ManufacturerPage() {
  const [list, setList] = useState<Manufacturer[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [data, setData] = useState<Insights | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .manufacturers()
      .then((ms) => {
        const own = getSession()?.manufacturer_id;
        const visible = own ? ms.filter((m) => m.id === own) : ms;
        setList(visible);
        if (visible.length) setSelected(visible[0].id);
      })
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (selected == null) return;
    setData(null);
    api.insights(selected).then(setData).catch((e) => setError(e.message));
  }, [selected]);

  const maxTopic = Math.max(1, ...(data?.topics.map((t) => t.count) ?? [1]));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Ishlab chiqaruvchi paneli</h1>
          <p className="text-sm text-gray-500">Anonim va jamlangan maʼlumot: dorilaringizga qiziqish va xaridorlar shubhalanayotgan mavzular.</p>
        </div>
        <select
          value={selected ?? ""}
          onChange={(e) => setSelected(Number(e.target.value))}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2"
        >
          {list.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name} ({m.is_local ? "mahalliy" : m.country})
            </option>
          ))}
        </select>
      </div>

      {error && <p className="rounded-lg bg-red-50 p-3 text-red-700">{error}</p>}
      {!data ? (
        <p className="text-gray-500">Yuklanmoqda…</p>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <Stat label="Ishonch kartasi ochilgan" value={data.total_views} />
            <Stat label="AI ga berilgan savollar" value={data.total_questions} />
            <Stat label="Preparatlar" value={data.drugs.length} />
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <section className="rounded-2xl border border-gray-200 bg-white p-6">
              <h2 className="font-semibold">Savollar mavzulari</h2>
              <p className="mb-4 text-sm text-gray-500">Xaridorlar nimada shubhalanyapti</p>
              <ul className="space-y-2">
                {data.topics.map((t) => (
                  <li key={t.topic}>
                    <div className="flex justify-between text-sm">
                      <span>{t.label}</span>
                      <span className="text-gray-500">{t.count}</span>
                    </div>
                    <div className="mt-1 h-2 rounded-full bg-gray-100">
                      <div className="h-2 rounded-full bg-brand-500" style={{ width: `${(t.count / maxTopic) * 100}%` }} />
                    </div>
                  </li>
                ))}
                {data.topics.length === 0 && <li className="text-sm text-gray-500">Hali savollar yoʻq.</li>}
              </ul>
            </section>

            <section className="rounded-2xl border border-gray-200 bg-white p-6">
              <h2 className="font-semibold">Preparatlar boʻyicha qiziqish</h2>
              <table className="mt-3 w-full text-sm">
                <thead className="text-left text-gray-500">
                  <tr>
                    <th className="py-1 font-medium">Preparat</th>
                    <th className="py-1 text-right font-medium">Koʻrishlar</th>
                    <th className="py-1 text-right font-medium">Savollar</th>
                  </tr>
                </thead>
                <tbody>
                  {data.drugs.map((s) => (
                    <tr key={s.drug.id} className="border-t border-gray-50">
                      <td className="py-1.5">
                        <Link href={`/drug/${s.drug.id}`} className="text-brand-700 hover:underline">
                          {s.drug.trade_name}
                        </Link>{" "}
                        <span className="text-gray-500">{s.drug.strength}</span>
                      </td>
                      <td className="py-1.5 text-right">{s.views}</td>
                      <td className="py-1.5 text-right">{s.questions}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          </div>

          {data.manufacturer.is_local && (
            <section className="rounded-2xl border border-gray-200 bg-white p-6">
              <h2 className="font-semibold">Raqobatdagi import preparatlar</h2>
              <p className="mb-3 text-sm text-gray-500">Bir xil taʼsir qiluvchi modda, doza va shakl. Farq sizning preparatingizga nisbatan.</p>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[520px] text-sm">
                  <thead className="text-left text-gray-500">
                    <tr>
                      <th className="py-1 font-medium">Import preparat</th>
                      <th className="py-1 font-medium">Ishlab chiqaruvchi</th>
                      <th className="py-1 text-right font-medium">Narx</th>
                      <th className="py-1 text-right font-medium">Sizdan qimmatroq</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.competing_imports.map((a) => (
                      <tr key={a.drug.id} className="border-t border-gray-50">
                        <td className="py-1.5">
                          {a.drug.trade_name} <span className="text-gray-500">{a.drug.inn} {a.drug.strength}</span>
                        </td>
                        <td className="py-1.5 text-gray-600">{a.drug.manufacturer.name}, {a.drug.manufacturer.country}</td>
                        <td className="py-1.5 text-right">{som(a.drug.price_uzs)}</td>
                        <td className="py-1.5 text-right">{a.price_diff_pct > 0 ? `+${a.price_diff_pct}%` : `${a.price_diff_pct}%`}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
          <p className="text-xs text-gray-500">
            Panel maʼlumotlari reyting yoki reklama uchun ishlatilmaydi. Toʻlov Ishonch kartasidagi faktlarga taʼsir qilmaydi.
          </p>
        </>
      )}
    </div>
  );
}
