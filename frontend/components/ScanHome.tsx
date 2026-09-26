"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { getLocation } from "@/lib/geo";
import { api, Mode, NearbyPharmacy, Participant, VerifyInput, VerifyResponse, Wallet } from "@/lib/api";
import { getDeviceId } from "@/lib/device";
import { CameraScanner } from "@/components/CameraScanner";
import { VerifyResult } from "@/components/VerifyResult";
import { Icon } from "@/components/Icon";
import { MedicineIllustration } from "@/components/MedicineIllustration";
import { PharmacyMap } from "@/components/PharmacyMap";

export function ScanHome({ initialMode, initialPharmacyId }: { initialMode: Mode; initialPharmacyId: number | null }) {
  const [mode, setMode] = useState<Mode>(initialMode);
  const [pharmacies, setPharmacies] = useState<Participant[]>([]);
  const [pharmacyId, setPharmacyId] = useState<number | null>(initialPharmacyId);
  const [camera, setCamera] = useState(false);
  const [manual, setManual] = useState(false);
  const [code, setCode] = useState("");
  const [gtin, setGtin] = useState("");
  const [serial, setSerial] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [nearby, setNearby] = useState<NearbyPharmacy[]>([]);
  const [locating, setLocating] = useState(false);
  const [result, setResult] = useState<VerifyResponse | null>(null);
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [lastInput, setLastInput] = useState<Omit<VerifyInput, "mode" | "pharmacy_id"> | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const resultRef = useRef<HTMLDivElement>(null);
  const codeRef = useRef<HTMLInputElement>(null);

  const refreshWallet = useCallback(() => { api.wallet(getDeviceId()).then(setWallet).catch(() => {}); }, []);
  useEffect(() => {
    api.pharmacies().then(rows => {
      const available = rows.filter(pharmacy => !pharmacy.is_demo);
      setPharmacies(available);
      setPharmacyId(current => available.some(pharmacy => pharmacy.id === current) ? current : null);
    }).catch(() => {});
    refreshWallet();
  }, [refreshWallet]);
  useEffect(() => { if (manual) codeRef.current?.focus(); }, [manual]);
  useEffect(() => {
    if (!result) return;
    resultRef.current?.focus({ preventScroll: true });
    resultRef.current?.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth", block: "start" });
  }, [result]);

  const run = useCallback(async (request: Promise<VerifyResponse>) => {
    setBusy(true);
    setError("");
    setResult(null);
    try { setResult(await request); refreshWallet(); }
    catch (failure) { setError((failure as Error).message); }
    finally { setBusy(false); }
  }, [refreshWallet]);

  const verify = useCallback((input: Omit<VerifyInput, "mode" | "pharmacy_id">, nextMode: Mode = mode) => {
    setLastInput(input);
    return run(getLocation().then(location => api.verify({ ...input, mode: nextMode, pharmacy_id: pharmacyId, device_id: getDeviceId(), lat: location?.lat, lon: location?.lon })));
  }, [run, mode, pharmacyId]);

  const purchase = useCallback(async (price: number | null) => {
    if (!lastInput) return;
    setMode("after");
    await verify({ ...lastInput, price_paid: price }, "after");
  }, [lastInput, verify]);

  const onCameraCode = useCallback((text: string) => { setCamera(false); verify({ code: text }); }, [verify]);

  function onFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (file.size > 8 * 1024 * 1024) { setError("Surat hajmi 8 MB dan kichik boʻlsin. Kichikroq surat tanlang."); return; }
    setLastInput(null);
    const form = new FormData();
    form.append("file", file);
    form.append("mode", mode);
    if (pharmacyId) form.append("pharmacy_id", String(pharmacyId));
    form.append("device_id", getDeviceId());
    run(getLocation().then(location => {
      if (location) { form.append("lat", String(location.lat)); form.append("lon", String(location.lon)); }
      return api.verifyImage(form);
    }));
  }

  function locate() {
    if (!navigator.geolocation) { setError("Joylashuvni aniqlab boʻlmadi. Dorixonani roʻyxatdan tanlashingiz mumkin."); return; }
    setLocating(true);
    setError("");
    navigator.geolocation.getCurrentPosition(async position => {
      try {
        const found = (await api.nearby(position.coords.latitude, position.coords.longitude)).filter(item => !item.pharmacy.is_demo);
        setNearby(found);
        if (found[0]) {
          setPharmacyId(found[0].pharmacy.id);
          setPharmacies(previous => {
            const ids = new Set(previous.map(pharmacy => pharmacy.id));
            return [...found.map(item => item.pharmacy).filter(pharmacy => !ids.has(pharmacy.id)), ...previous];
          });
        } else setError("Yaqinda Namangan dorixonasi topilmadi. Xaritadan tanlang.");
      } catch (failure) { setError((failure as Error).message); }
      finally { setLocating(false); }
    }, () => { setLocating(false); setError("Joylashuvga ruxsat berilmadi. Dorixonani roʻyxatdan tanlang."); }, { enableHighAccuracy: true, timeout: 10000 });
  }

  const selectedPharmacy = pharmacies.find(pharmacy => pharmacy.id === pharmacyId);

  return <>
    <div className="page-heading"><div><h1>Dori qutisini tekshiring</h1></div><span className="demo-pill"><Icon name="pin" size={15} />Namangan · Demo</span></div>
    <div className="home-grid">
      <div className="home-primary">
        <section className="scan-hero" aria-labelledby="scan-title" aria-busy={busy}>
          <div className="hero-top"><div className="hero-copy"><h2 id="scan-title">Kodni<br /><span>skanerlang.</span></h2><p>Qutidagi kichik kvadrat kodni kameraga tuting.</p></div><MedicineIllustration /></div>
          <div className="hero-controls">
            {mode === "after" && <p className="info-notice mb-4"><Icon name="info" size={18} />Sotib olingan qutini qayd qilish rejimi.</p>}
            {camera ? <CameraScanner onCode={onCameraCode} onClose={() => setCamera(false)} /> : <button type="button" className="primary-button scan-button" onClick={() => { setCamera(true); setManual(false); setError(""); }} disabled={busy}><Icon name="scan" size={26} /><span>{busy ? "Tekshirilmoqda…" : "Qutini tekshirish"}</span><Icon name="arrow" /></button>}
            <input ref={fileRef} type="file" accept="image/*" onChange={onFile} className="hidden" aria-label="Quti suratini tanlash" />
            <div className="scan-alternatives"><button type="button" className="secondary-button" onClick={() => fileRef.current?.click()} disabled={busy}><Icon name="camera" size={21} />Suratdan tekshirish</button><button type="button" className="secondary-button" aria-expanded={manual} aria-controls="manual-entry" onClick={() => { setManual(!manual); setCamera(false); }} disabled={busy}><Icon name="keyboard" size={21} />Kodni yozish</button></div>
            <p className="camera-note"><Icon name="user" size={14} /><span>Tekshirish uchun kirish shart emas. Ball yigʻish uchun akkaunt kerak.</span></p>
            {manual && <form id="manual-entry" className="manual-form" onSubmit={event => { event.preventDefault(); if (code.trim()) verify({ code: code.trim() }); else if (gtin.trim()) verify({ gtin: gtin.trim(), serial: serial.trim() || undefined }); }}>
              <div><label htmlFor="package-code" className="field-label">Qutidagi kod</label><input ref={codeRef} id="package-code" value={code} onChange={event => setCode(event.target.value)} placeholder="Kod ostidagi yozuvni kiriting" className="text-input" aria-describedby="code-help" /><p id="code-help" className="field-help">Kvadrat kod yonidagi yozuvni toʻliq koʻchiring.</p></div>
              <details><summary className="subtle-link">Kod ikki qismga boʻlinganmi?</summary><div className="field-grid mt-3"><div><label htmlFor="package-number" className="field-label">(01) dan keyingi raqamlar</label><input id="package-number" value={gtin} onChange={event => setGtin(event.target.value)} inputMode="numeric" placeholder="14 ta raqam" className="text-input" /></div><div><label htmlFor="package-serial" className="field-label">(21) yoki SN dan keyingi yozuv</label><input id="package-serial" value={serial} onChange={event => setSerial(event.target.value)} placeholder="Qutining alohida raqami" className="text-input" /></div></div></details>
              <button className="primary-button" disabled={busy || (!code.trim() && !gtin.trim())}><Icon name="search" size={20} />{busy ? "Tekshirilmoqda…" : "Kodni tekshirish"}</button>
            </form>}
          </div>
        </section>

        {busy && <div className="card loading-notice" role="status"><span className="spinner" aria-hidden="true" />Quti haqidagi maʼlumotlar tekshirilmoqda…</div>}
        {error && <div className="error-notice" role="alert">{error}</div>}
        {result && <div ref={resultRef} tabIndex={-1} className="scan-result" aria-label="Tekshiruv natijasi"><VerifyResult key={result.scan_id ?? result.headline} r={result} onPurchase={mode === "before" && lastInput ? purchase : undefined} /></div>}

        <section className="card pharmacy-picker" aria-labelledby="pharmacy-title"><div className="picker-title"><span className="step-symbol"><Icon name="pin" /></span><div><h2 id="pharmacy-title">Dorixonani tanlang</h2><p>Namangan · ixtiyoriy</p></div></div><label htmlFor="pharmacy" className="sr-only">Dorixonani tanlang</label><select id="pharmacy" value={pharmacyId ?? ""} onChange={event => setPharmacyId(event.target.value ? Number(event.target.value) : null)} className="text-input"><option value="">Tanlanmagan</option>{pharmacies.map(pharmacy => <option key={pharmacy.id} value={pharmacy.id}>{pharmacy.name}</option>)}</select>{selectedPharmacy && <p className="field-help">{selectedPharmacy.address || selectedPharmacy.region}</p>}<div className="picker-actions"><button type="button" className="secondary-button" onClick={locate} disabled={locating}><Icon name="locate" size={19} />{locating ? "Qidirilmoqda…" : "Yaqinimdagi dorixona"}</button><Link href="/xarita" className="secondary-button"><Icon name="map" size={19} />Xaritadan tanlash</Link></div>{nearby.length > 0 && <div className="map-filters">{nearby.slice(0, 4).map(item => <button type="button" key={item.pharmacy.id} aria-pressed={pharmacyId === item.pharmacy.id} onClick={() => setPharmacyId(item.pharmacy.id)}>{item.pharmacy.name} · {item.distance_m} m</button>)}</div>}</section>
      </div>

      <aside className="home-aside" aria-label="Foydali imkoniyatlar">
        <section className="map-teaser"><div className="map-teaser-copy"><h2>Namangan dorixonalari</h2></div><PharmacyMap compact /><Link href="/xarita" className="subtle-link">Xaritani ochish<Icon name="arrow" size={18} /></Link></section>
        <Link href="/ballar" className="reward-card"><span className="step-symbol"><Icon name="star" /></span><div><strong>{wallet ? `${wallet.points} demo ball` : "Ballarim"}</strong></div><Icon name="chevron" size={19} /></Link>
        <Link href="/yordamchi" className="secondary-button"><Icon name="chat" size={20} />Yordam kerakmi?</Link>
      </aside>
    </div>
  </>;
}
