"use client";

import "leaflet/dist/leaflet.css";
import type { Map as LeafletMap, Marker } from "leaflet";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { api, MapPharmacy } from "@/lib/api";
import { addBaseLayer } from "@/lib/tiles";
import { Icon } from "./Icon";

const NAMANGAN: [number, number] = [40.9983, 71.6726];
const distanceLabel = (meters: number) => meters < 1000 ? `${Math.round(meters)} m` : `${(meters / 1000).toFixed(1)} km`;

function distanceBetween(first: { lat: number; lon: number }, second: { lat: number; lon: number }) {
  const radians = (degrees: number) => degrees * Math.PI / 180;
  const square = Math.sin(radians(second.lat - first.lat) / 2) ** 2 + Math.cos(radians(first.lat)) * Math.cos(radians(second.lat)) * Math.sin(radians(second.lon - first.lon) / 2) ** 2;
  return 12742000 * Math.asin(Math.sqrt(Math.min(1, square)));
}

export function PharmacyMap({ mode = "public", height = "650px", compact = false }: { mode?: "public" | "risk"; height?: string; compact?: boolean }) {
  const box = useRef<HTMLDivElement>(null);
  const map = useRef<LeafletMap | null>(null);
  const leaflet = useRef<typeof import("leaflet") | null>(null);
  const markers = useRef<Marker[]>([]);
  const fitted = useRef(false);
  const [rows, setRows] = useState<MapPharmacy[]>([]);
  const [selected, setSelected] = useState<MapPharmacy | null>(null);
  const [me, setMe] = useState<{ lat: number; lon: number } | null>(null);
  const [nearOnly, setNearOnly] = useState(false);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);
  const [loading, setLoading] = useState(true);
  const [locating, setLocating] = useState(false);
  const [mapUnavailable, setMapUnavailable] = useState(false);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    (mode === "risk" ? api.mapInspector() : api.mapPharmacies().then(data => data.pharmacies))
      .then(data => { if (!cancelled) setRows(data.filter(pharmacy => /namangan/i.test(pharmacy.region) && (mode === "risk" || !pharmacy.is_demo))); })
      .catch(() => { if (!cancelled) setError("Dorixonalar yuklanmadi. Qayta urinib koʻring."); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [mode, retry]);

  useEffect(() => {
    let cancelled = false;
    import("leaflet").then(module => {
      if (cancelled || !box.current || map.current) return;
      leaflet.current = module;
      const instance = module.map(box.current, { zoomControl: false, scrollWheelZoom: false, dragging: !compact, touchZoom: !compact, doubleClickZoom: !compact, keyboard: !compact }).setView(NAMANGAN, 12);
      addBaseLayer(module, instance, () => { if (!cancelled) setMapUnavailable(true); });
      if (!compact) module.control.zoom({ position: "bottomright", zoomInTitle: "Yaqinlashtirish", zoomOutTitle: "Uzoqlashtirish" }).addTo(instance);
      instance.on("click", () => setSelected(null));
      map.current = instance;
      setReady(true);
    }).catch(() => { if (!cancelled) setMapUnavailable(true); });
    const observer = typeof ResizeObserver !== "undefined" ? new ResizeObserver(() => map.current?.invalidateSize()) : null;
    if (box.current) observer?.observe(box.current);
    return () => { cancelled = true; observer?.disconnect(); map.current?.remove(); map.current = null; markers.current = []; fitted.current = false; };
  }, [compact]);

  const shown = useMemo(() => {
    let list = rows.map(pharmacy => me ? { ...pharmacy, distance_m: distanceBetween(me, pharmacy) } : pharmacy);
    if (nearOnly && me) list = list.filter(pharmacy => (pharmacy.distance_m ?? Infinity) < 5000);
    if (query.trim()) list = list.filter(pharmacy => `${pharmacy.name} ${pharmacy.address}`.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()));
    return list.sort((first, second) => me ? (first.distance_m ?? Infinity) - (second.distance_m ?? Infinity) : first.name.localeCompare(second.name));
  }, [rows, me, nearOnly, query]);

  function choose(pharmacy: MapPharmacy) {
    setSelected(pharmacy);
    map.current?.setView([pharmacy.lat, pharmacy.lon], 15);
    if (matchMedia("(max-width: 600px)").matches) box.current?.scrollIntoView({ block: "center" });
  }

  useEffect(() => {
    const instance = map.current;
    const module = leaflet.current;
    if (!instance || !module) return;
    markers.current.forEach(marker => marker.remove());
    markers.current = shown.map(pharmacy => {
      const icon = module.divIcon({ html: '<span style="display:grid;place-items:center;width:34px;height:34px;background:#286a4d;color:white;border:3px solid white;border-radius:12px;box-shadow:0 2px 8px #20352b40;font-size:24px;font-weight:700">+</span>', className: "pharmacy-marker", iconSize: [34, 34], iconAnchor: [17, 17] });
      return module.marker([pharmacy.lat, pharmacy.lon], { icon, title: pharmacy.name, alt: pharmacy.name, keyboard: !compact, interactive: !compact }).on("click", event => { module.DomEvent.stopPropagation(event); choose(pharmacy); }).addTo(instance);
    });
    if (!fitted.current && shown.length) {
      fitted.current = true;
      instance.fitBounds(module.latLngBounds(shown.map(pharmacy => [pharmacy.lat, pharmacy.lon] as [number, number])), { padding: [30, 30], maxZoom: 14 });
    }
  }, [shown, ready, compact]);

  function locate() {
    if (!navigator.geolocation) { setError("Joylashuv aniqlanmadi. Nom boʻyicha qidiring."); return; }
    setLocating(true);
    setError("");
    navigator.geolocation.getCurrentPosition(position => {
      const here = { lat: position.coords.latitude, lon: position.coords.longitude };
      const closest = rows.filter(pharmacy => distanceBetween(here, pharmacy) < 5000);
      if (!closest.length) {
        setError("5 km ichida Namangan dorixonasi topilmadi.");
        setLocating(false);
        return;
      }
      setMe(here);
      setNearOnly(true);
      setQuery("");
      setSelected(null);
      fitted.current = false;
      setLocating(false);
    }, () => { setLocating(false); setError("Joylashuvga ruxsat berilmadi."); }, { enableHighAccuracy: true, timeout: 10000 });
  }

  return <div className={compact ? "map-workspace map-preview" : "map-workspace"} style={compact ? undefined : { height }}>
    {!compact && <section className="map-sidebar" aria-label="Dorixonalar roʻyxati">
      <label className="map-search"><Icon name="search" size={18} /><input aria-label="Dorixona yoki manzilni qidirish" placeholder="Dorixona nomi yoki manzil" value={query} onChange={event => { setQuery(event.target.value); setSelected(null); }} /></label>
      <div className="map-filters"><button type="button" aria-pressed={!nearOnly} onClick={() => { setNearOnly(false); setQuery(""); setError(""); fitted.current = false; }}>Hammasi</button><button type="button" disabled={locating || loading} aria-pressed={nearOnly} onClick={locate}>{locating ? "Aniqlanmoqda…" : "Yaqinimda"}</button></div>
      {error && <div className="error-notice text-sm" role="alert">{error}<button type="button" className="subtle-link" onClick={() => setRetry(value => value + 1)}>Qayta yuklash</button></div>}
      <div className="pharmacy-list" aria-busy={loading}>{loading ? <div className="loading-notice" role="status"><span className="spinner" />Yuklanmoqda…</div> : shown.length === 0 ? <p className="map-empty">Dorixona topilmadi.</p> : shown.map(pharmacy => <button type="button" key={pharmacy.id} className={`pharmacy-list-item${selected?.id === pharmacy.id ? " active" : ""}`} onClick={() => choose(pharmacy)} aria-pressed={selected?.id === pharmacy.id}><span className="step-symbol"><Icon name="plus" size={20} /></span><span><strong>{pharmacy.name}</strong><small>{pharmacy.address || "Manzil kiritilmagan"}</small>{pharmacy.distance_m != null && <small>{distanceLabel(pharmacy.distance_m)}</small>}</span></button>)}</div>
    </section>}
    <div className="map-stage">
      <div ref={box} className="map-canvas" aria-label="Namangan dorixonalari xaritasi" />
      {!compact && <div className="map-status" role="status"><Icon name="pin" size={15} />{loading ? "Yuklanmoqda…" : `${shown.length} ta dorixona`}</div>}
      {mapUnavailable && <div className="map-status" role="status">Xarita yuklanmadi. Roʻyxatdan tanlang.</div>}
      {!compact && selected && <section className="map-selection" aria-label="Tanlangan dorixona"><button type="button" className="icon-button map-selection-close" onClick={() => setSelected(null)} aria-label="Dorixona maʼlumotini yopish"><Icon name="close" size={19} /></button><h3>{selected.name}</h3><p>{selected.address || "Manzil kiritilmagan"}</p><div className="map-selection-actions">{mode === "public" && <Link href={`/?dorixona=${selected.id}`} className="primary-button"><Icon name="check" size={17} />Shu dorixonadaman</Link>}<a href={`https://www.google.com/maps/dir/?api=1&destination=${selected.lat},${selected.lon}`} target="_blank" rel="noreferrer" className="secondary-button"><Icon name="arrow" size={17} />Yoʻlni koʻrsatish</a></div></section>}
    </div>
  </div>;
}
