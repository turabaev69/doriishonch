import type { Map as LeafletMap } from "leaflet";

export function addBaseLayer(leaflet: typeof import("leaflet"), map: LeafletMap, onUnavailable?: () => void) {
  const sources = [
    { url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png", options: { maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' } },
    { url: "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", options: { maxZoom: 19, subdomains: "abcd", attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>' } },
  ];
  function load(index: number) {
    const source = sources[index];
    const layer = leaflet.tileLayer(source.url, source.options);
    let errors = 0;
    let loaded = 0;
    let failed = false;
    layer.on("tileload", () => { loaded += 1; });
    layer.on("tileerror", () => {
      errors += 1;
      if (failed || loaded > 0 || errors < 3) return;
      failed = true;
      if (index + 1 < sources.length) {
        map.removeLayer(layer);
        load(index + 1);
      } else onUnavailable?.();
    });
    layer.addTo(map);
  }
  load(0);
}
