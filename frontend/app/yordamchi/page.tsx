"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { getDeviceId } from "@/lib/device";
import { ChatBox } from "@/components/ChatBox";
import { Icon } from "@/components/Icon";

export default function Assistant() {
  const [ai, setAi] = useState<boolean | null>(null);
  const [location, setLocation] = useState<{ lat: number; lon: number } | null>(null);
  const [locating, setLocating] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { api.aiStatus().then(status => setAi(status.ai_enabled)).catch(() => setAi(false)); }, []);
  function locate() {
    if (!navigator.geolocation) { setError("Joylashuvni aniqlab boʻlmadi. Savolingizda manzilingizni yozishingiz mumkin."); return; }
    setLocating(true);
    setError("");
    navigator.geolocation.getCurrentPosition(position => { setLocation({ lat: position.coords.latitude, lon: position.coords.longitude }); setLocating(false); }, () => { setLocating(false); setError("Joylashuvga ruxsat berilmadi. Yordamchidan joylashuvsiz ham foydalanishingiz mumkin."); }, { timeout: 10000 });
  }
  return <div className="mx-auto max-w-3xl space-y-5">
    <div className="page-heading"><div><h1>Yordamchi</h1></div></div>
    {ai === false && <div className="info-notice"><Icon name="info" size={19} /><p>AI ulanmagan. Tayyor javoblar rejimi.</p></div>}
    <ChatBox intro="Quti yoki tekshiruv haqida savolingizni yozing." placeholder="Savolingiz…" suggestions={["Qutini qanday tekshiraman?", "Natija nimani bildiradi?", "Namanganda dorixona topish"]} send={messages => api.chat({ messages, device_id: getDeviceId(), lat: location?.lat, lon: location?.lon })} />
    <div className="flex flex-wrap items-center justify-between gap-3"><button type="button" onClick={locate} disabled={locating} className="subtle-link"><Icon name={location ? "check" : "locate"} size={18} />{locating ? "Joylashuv aniqlanmoqda…" : location ? "Joylashuv ulandi" : "Yaqin dorixonalar uchun joylashuvni ulash"}</button><p className="text-sm text-slate-500">AI javobida xato boʻlishi mumkin.</p></div>
    {error && <p role="alert" className="error-notice">{error}</p>}
    <p className="text-sm text-slate-500">Tashxis va davolash uchun shifokorga murojaat qiling.</p>
  </div>;
}
