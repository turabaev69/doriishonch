"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { MlPanel } from "@/components/MlPanel";
import { PackNetDemo } from "@/components/PackNetDemo";

const FEATURES = [
  ["🧠", "Skan xavf modeli (oʻz modelimiz)", "Har skan uchun qalbaki boʻlish ehtimoli va sabablari: quti tarixi, narx, dorixona va partiya signallari. Inspektor tasdiqlaridan oʻrganadi.", "/inspektor", false],
  ["📦", "PackNet — qadoq surati modeli (oʻz modelimiz)", "Qutining suratidan qaysi dori ekanini va asl dizayndan farqini topadi. Telefonda internetsiz ishlaydi.", "/ai", false],
  ["🤖", "AI yordamchi (agent)", "Claude vositalar bilan ishlaydi: qutini tekshiradi, dorini qidiradi, Ishonch kartasi, analoglar, zanjir tarixi, yaqin dorixonalar. Qaysi vositani ishlatganini koʻrsatadi.", "/yordamchi", true],
  ["🕵️", "Inspektor copiloti (agent)", "\"Qaysi dorixonani birinchi tekshiray?\" — xavf signallari, ogohlantirishlar, zanjir va bojxona maʼlumotlaridan xulosa.", "/inspektor", true],
  ["📦", "Qadoq ekspertizasi (vision)", "Qutining surati: ochilganlik belgilari, bosma sifati; qutiga bosilgan seriya va muddat kod maʼlumotlari bilan solishtiriladi.", "/", true],
  ["📷", "Suratdan kod oʻqish (vision)", "Kamera DataMatrix ni oʻqiy olmasa, AI qutidagi GTIN va seriya raqamini suratdan oʻqiydi.", "/", true],
  ["💬", "Natijani tushuntirish", "Qoidalar tizimi xulosasini oddiy oʻzbek tilida tushuntiradi (xulosani oʻzgartirmaydi).", "/", true],
  ["🧾", "Bojxona tavsifini moslash", "Deklaratsiyadagi erkin matnni (masalan, \"AMOXICILLIN 500MG CAPS\") dori reestriga moslaydi.", "/bojxona", true],
  ["📚", "Ishonch kartasi savol-javob (RAG)", "Dori haqidagi savollarga faqat rasmiy faktlar asosida, manba raqamlari bilan javob.", "/dori", true],
  ["📈", "Dorixonalar anomaliyasi (ML)", "IsolationForest dorixonalar xatti-harakatidagi gʻayrioddiylikni topadi (API kalitsiz ham ishlaydi).", "/inspektor", false],
  ["🛡️", "Xavfsizlik filtri", "Doza, tashxis, davolash savollarini bloklaydi; \"eng yaxshi\" kabi reklama iboralarini olib tashlaydi.", "/yordamchi", false],
] as const;

export default function AiPage() {
  const [status, setStatus] = useState<{ ai_enabled: boolean; model: string | null } | null>(null);
  useEffect(() => {
    api.aiStatus().then(setStatus).catch(() => {});
  }, []);
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Dasturda AI qayerda ishlaydi</h1>
        <p className="text-sm text-gray-600">
          Qizil/yashil xulosani tushuntirib boʻladigan qoidalar chiqaradi, AI esa koʻrish, tushunish, qidirish va tahlil qiladi.
        </p>
        {status && (
          <p className={`mt-2 inline-block rounded-lg px-3 py-1 text-sm ${status.ai_enabled ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-900"}`}>
            {status.ai_enabled ? `AI ulangan: ${status.model}` : "AI kaliti ulanmagan: Claude talab qiladigan funksiyalar soddalashtirilgan rejimda"}
          </p>
        )}
      </div>
      <PackNetDemo />
      <MlPanel canRetrain={false} />
      <h2 className="pt-2 text-lg font-semibold">Barcha AI funksiyalar</h2>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map(([icon, title, text, href, needsKey]) => (
          <Link key={title} href={href} className="rounded-2xl border border-gray-200 bg-white p-5 hover:border-brand-500">
            <div className="text-2xl">{icon}</div>
            <div className="mt-2 font-semibold">{title}</div>
            <p className="text-sm text-gray-600">{text}</p>
            <div className="mt-2 text-xs text-gray-400">{needsKey ? "Claude API" : "Mahalliy model / qoidalar"}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
