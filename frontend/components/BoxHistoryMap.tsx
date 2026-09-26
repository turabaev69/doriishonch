"use client";

import "leaflet/dist/leaflet.css";
import type { Map as LMap } from "leaflet";
import { useEffect, useRef } from "react";
import type { Place } from "@/lib/api";
import { fmtDateTime } from "@/lib/api";
import { addBaseLayer } from "@/lib/tiles";

const COLOR: Record<string, string> = {
  purchase: "#DC2626", disputed: "#DC2626", sold: "#DC2626", scan: "#2563EB", received: "#16A34A", customs_cleared: "#16A34A",
};

/** Qutining tarixi xaritada: qayerda sotilgan (qizil), tekshirilgan (koʻk), dorixonaga kelgan (yashil). */
export function BoxHistoryMap({ places }: { places: Place[] }) {
  const box = useRef<HTMLDivElement>(null);
  const map = useRef<LMap | null>(null);

  useEffect(() => {
    let dead = false;
    import("leaflet").then((mod) => {
      if (dead || !box.current || map.current) return;
      const m = mod.map(box.current, { zoomControl: true, scrollWheelZoom: false }).setView([41.3, 69.28], 11);
      addBaseLayer(mod, m);
      const pts: [number, number][] = [];
      // Bir joydagi bir xil turdagi hodisalarni birlashtiramiz
      const groups = new Map<string, Place[]>();
      for (const p of places) {
        const k = `${p.kind === "disputed" ? "purchase" : p.kind}:${p.lat.toFixed(3)},${p.lon.toFixed(3)}`;
        groups.set(k, [...(groups.get(k) ?? []), p]);
      }
      for (const list of groups.values()) {
        const p = list[list.length - 1];
        const color = COLOR[p.kind] ?? "#64748B";
        const sold = ["purchase", "disputed", "sold"].includes(p.kind);
        const marker = mod.circleMarker([p.lat, p.lon], {
          radius: sold ? 12 : 9, color: "#fff", weight: 3, fillColor: color, fillOpacity: 1,
        }).addTo(m);
        marker.bindPopup(`<b>${p.label}${list.length > 1 ? ` · ${list.length} marta` : ""}</b><br>${p.place || ""}` +
          `${p.at ? `<br>${fmtDateTime(p.at)}` : ""}${p.me ? "<br><i>siz</i>" : ""}`);
        pts.push([p.lat, p.lon]);
      }
      if (pts.length > 1) m.fitBounds(mod.latLngBounds(pts), { padding: [30, 30], maxZoom: 15 });
      else if (pts.length === 1) m.setView(pts[0], 14);
      map.current = m;
    });
    return () => {
      dead = true;
      map.current?.remove();
      map.current = null;
    };
  }, [places]);

  const sold = places.filter((p) => ["purchase", "disputed", "sold"].includes(p.kind));
  const scans = places.filter((p) => p.kind === "scan");

  return (
    <div className="card space-y-3">
      <div className="flex items-center gap-3">
        <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-blue-50 text-lg">🗺️</div>
        <div className="flex-1">
          <div className="font-semibold">Qutining tarixi xaritada</div>
          <div className="text-xs text-slate-500">
            {sold.length ? `${sold.length} marta sotilgan` : "Sotilgani qayd etilmagan"} · {scans.length} marta tekshirilgan
          </div>
        </div>
      </div>
      <div ref={box} className="h-64 w-full overflow-hidden rounded-2xl" />
      <div className="flex flex-wrap gap-3 text-xs font-semibold text-slate-600">
        <span className="flex items-center gap-1"><span className="h-3 w-3 rounded-full bg-[#DC2626]" />sotilgan</span>
        <span className="flex items-center gap-1"><span className="h-3 w-3 rounded-full bg-[#2563EB]" />tekshirilgan</span>
        <span className="flex items-center gap-1"><span className="h-3 w-3 rounded-full bg-[#16A34A]" />dorixonaga kelgan</span>
      </div>
      {sold.length > 0 && (
        <ul className="space-y-1 text-sm">
          {sold.slice(-3).reverse().map((p, i) => (
            <li key={i} className="flex gap-2">
              <span className="text-red-600">●</span>
              <span><b>{p.label}</b>{p.place ? ` — ${p.place}` : ""}{p.at ? `, ${fmtDateTime(p.at)}` : ""}{p.me ? " (siz)" : ""}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
