import { Ionicons } from "@expo/vector-icons";
import * as Location from "expo-location";
import { useFocusEffect, useRouter } from "expo-router";
import { useCallback, useMemo, useRef, useState } from "react";
import { ActivityIndicator, Linking, Platform, Pressable, StyleSheet, Text, View } from "react-native";
import MapView, { Marker, Region } from "react-native-maps";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { tap } from "../../components/ui";
import { api } from "../../lib/api";
import { setPharmacy } from "../../lib/store";
import { C, R, shadow } from "../../lib/theme";
import type { MapPharmacy } from "../../lib/types";

const UZ: Region = { latitude: 41.0, longitude: 64.6, latitudeDelta: 9, longitudeDelta: 13 };
type Filter = "all" | "mission" | "near";

const dist = (m: number) => (m < 1000 ? `${Math.round(m)} m` : `${(m / 1000).toFixed(1)} km`);

function haversine(a: { lat: number; lon: number }, b: { lat: number; lon: number }) {
  const r = (x: number) => (x * Math.PI) / 180;
  const d = Math.sin(r(b.lat - a.lat) / 2) ** 2 + Math.cos(r(a.lat)) * Math.cos(r(b.lat)) * Math.sin(r(b.lon - a.lon) / 2) ** 2;
  return 12742000 * Math.asin(Math.sqrt(d));
}

export default function MapScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const map = useRef<MapView>(null);
  const [rows, setRows] = useState<MapPharmacy[]>([]);
  const [near, setNear] = useState<MapPharmacy[]>([]);
  const [me, setMe] = useState<{ lat: number; lon: number } | null>(null);
  const [sel, setSel] = useState<MapPharmacy | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useFocusEffect(
    useCallback(() => {
      api.mapPharmacies().then((d) => { setRows(d.pharmacies); setErr(""); })
        .catch((e) => setErr((e as Error).message));
    }, []),
  );

  async function locate() {
    tap();
    setBusy(true);
    setErr("");
    try {
      const perm = await Location.requestForegroundPermissionsAsync();
      if (!perm.granted) throw new Error("Joylashuvga ruxsat bering (Sozlamalar → DoriIshonch)");
      const pos = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
      const here = { lat: pos.coords.latitude, lon: pos.coords.longitude };
      setMe(here);
      setFilter("near");
      map.current?.animateToRegion({ latitude: here.lat, longitude: here.lon, latitudeDelta: 0.03, longitudeDelta: 0.03 }, 600);
      // Atrofdagi haqiqiy dorixonalar (OpenStreetMap)
      api.nearby(here.lat, here.lon)
        .then((list) => setNear(list.filter((x) => x.pharmacy.lat && x.pharmacy.lon).map((x) => ({
          ...x.pharmacy, lat: x.pharmacy.lat as number, lon: x.pharmacy.lon as number, region_key: null,
          distance_m: x.distance_m, osm: true,
        }))))
        .catch(() => {});
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const shown = useMemo(() => {
    const byId = new Map<number, MapPharmacy>();
    for (const p of [...rows, ...near]) byId.set(p.id, { ...byId.get(p.id), ...p });
    let list = [...byId.values()].map((p) => (me ? { ...p, distance_m: p.distance_m ?? haversine(me, p) } : p));
    if (filter === "mission") list = list.filter((p) => p.mission_points);
    if (filter === "near" && me) list = list.filter((p) => (p.distance_m ?? 1e9) < 5000);
    return list;
  }, [rows, near, me, filter]);

  function select(p: MapPharmacy) {
    tap();
    setSel(p);
    map.current?.animateToRegion({ latitude: p.lat - 0.004, longitude: p.lon, latitudeDelta: 0.02, longitudeDelta: 0.02 }, 450);
  }

  async function here(p: MapPharmacy) {
    tap("success");
    await setPharmacy({ id: p.id, kind: "pharmacy", name: p.name, region: p.region, address: p.address,
      license_ok: p.license_ok, is_demo: p.is_demo, lat: p.lat, lon: p.lon });
    router.push("/");
  }

  function route(p: MapPharmacy) {
    const url = Platform.OS === "ios"
      ? `http://maps.apple.com/?daddr=${p.lat},${p.lon}&q=${encodeURIComponent(p.name)}`
      : `https://www.google.com/maps/dir/?api=1&destination=${p.lat},${p.lon}`;
    Linking.openURL(url);
  }

  const chips: [Filter, string, keyof typeof Ionicons.glyphMap][] = [
    ["all", "Hammasi", "apps"], ["mission", "Missiya", "star"], ["near", "Yaqinimda", "navigate"],
  ];

  return (
    <View style={{ flex: 1 }}>
      <MapView ref={map} style={StyleSheet.absoluteFill} initialRegion={UZ} showsUserLocation={!!me}
        showsCompass={false} showsPointsOfInterests={false} onPress={() => setSel(null)}>
        {shown.map((p) => {
          const active = sel?.id === p.id;
          const color = p.mission_points ? C.gold : p.osm ? C.info : C.brand;
          return (
            <Marker key={`${p.id}-${active}`} coordinate={{ latitude: p.lat, longitude: p.lon }}
              onPress={(e) => { e.stopPropagation(); select(p); }} tracksViewChanges={false}
              anchor={{ x: 0.5, y: 1 }}>
              <View style={{ alignItems: "center" }}>
                <View style={[st.pin, { backgroundColor: color, transform: [{ scale: active ? 1.25 : 1 }] }]}>
                  <Ionicons name={p.mission_points ? "star" : "medkit"} size={15} color="#fff" />
                </View>
                <View style={[st.pinTail, { borderTopColor: color }]} />
              </View>
            </Marker>
          );
        })}
      </MapView>

      <View style={[st.top, { paddingTop: insets.top + 8 }]} pointerEvents="box-none">
        <View style={st.titleBox}>
          <Text style={st.title}>Dorixonalar xaritasi</Text>
          <Text style={st.subtitle}>{shown.length} ta dorixona</Text>
        </View>
        <View style={st.chips}>
          {chips.map(([k, label, icon]) => (
            <Pressable key={k} onPress={() => (k === "near" && !me ? locate() : (tap(), setFilter(k)))}
              style={[st.chip, filter === k && st.chipOn]}>
              <Ionicons name={icon} size={14} color={filter === k ? "#fff" : C.text} />
              <Text style={[st.chipText, filter === k && { color: "#fff" }]}>{label}</Text>
            </Pressable>
          ))}
        </View>
        {err ? <Text style={st.err}>{err}</Text> : null}
      </View>

      <Pressable onPress={locate} style={[st.fab, { bottom: sel ? 250 : 28 }]}>
        {busy ? <ActivityIndicator color={C.brand} /> : <Ionicons name="locate" size={24} color={C.brand} />}
      </Pressable>

      {sel && (
        <View style={st.sheet}>
          <View style={{ flexDirection: "row", gap: 12, alignItems: "flex-start" }}>
            <View style={[st.sheetIcon, { backgroundColor: sel.mission_points ? C.goldBg : C.brandLight }]}>
              <Ionicons name={sel.mission_points ? "star" : "medkit"} size={22} color={sel.mission_points ? C.gold : C.brand} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={st.sheetTitle} numberOfLines={2}>{sel.name}</Text>
              <Text style={st.sheetSub} numberOfLines={2}>{[sel.address, sel.region].filter(Boolean).join(" · ")}</Text>
            </View>
            <Pressable onPress={() => setSel(null)} hitSlop={12}>
              <Ionicons name="close-circle" size={26} color={C.faint} />
            </Pressable>
          </View>
          <View style={st.facts}>
            {sel.distance_m != null && <Fact icon="walk" text={dist(sel.distance_m)} />}
            {sel.checks_30d != null && <Fact icon="shield-checkmark" text={`${sel.checks_30d} ta tekshiruv`} />}
            {sel.mission_points ? <Fact icon="star" text={`Missiya +${sel.mission_points}`} gold /> : null}
          </View>
          <View style={{ flexDirection: "row", gap: 10 }}>
            <Pressable onPress={() => here(sel)} style={[st.btn, { backgroundColor: C.brand }]}>
              <Ionicons name="checkmark-circle" size={18} color="#fff" />
              <Text style={st.btnText}>Shu yerdaman</Text>
            </Pressable>
            <Pressable onPress={() => route(sel)} style={[st.btn, { backgroundColor: "#EEF2F6" }]}>
              <Ionicons name="navigate" size={18} color={C.text} />
              <Text style={[st.btnText, { color: C.text }]}>Yoʻl</Text>
            </Pressable>
          </View>
        </View>
      )}
    </View>
  );
}

function Fact({ icon, text, gold }: { icon: keyof typeof Ionicons.glyphMap; text: string; gold?: boolean }) {
  return (
    <View style={[st.fact, gold && { backgroundColor: C.goldBg }]}>
      <Ionicons name={icon} size={14} color={gold ? "#B45309" : C.muted} />
      <Text style={{ fontSize: 13, fontWeight: "700", color: gold ? "#B45309" : C.body }}>{text}</Text>
    </View>
  );
}

const st = StyleSheet.create({
  pin: { width: 32, height: 32, borderRadius: 16, alignItems: "center", justifyContent: "center", borderWidth: 2.5,
    borderColor: "#fff", ...shadow },
  pinTail: { width: 0, height: 0, borderLeftWidth: 6, borderRightWidth: 6, borderTopWidth: 8, borderLeftColor: "transparent",
    borderRightColor: "transparent", marginTop: -2 },
  top: { position: "absolute", top: 0, left: 0, right: 0, paddingHorizontal: 16, gap: 10 },
  titleBox: { alignSelf: "flex-start", backgroundColor: "rgba(255,255,255,0.95)", borderRadius: R.md, paddingHorizontal: 14,
    paddingVertical: 8, ...shadow },
  title: { fontSize: 18, fontWeight: "900", color: C.text },
  subtitle: { fontSize: 12, color: C.muted, fontWeight: "600" },
  chips: { flexDirection: "row", gap: 8 },
  chip: { flexDirection: "row", alignItems: "center", gap: 6, backgroundColor: "#fff", paddingHorizontal: 14, paddingVertical: 9,
    borderRadius: R.pill, ...shadow },
  chipOn: { backgroundColor: C.brand },
  chipText: { fontWeight: "700", color: C.text, fontSize: 14 },
  err: { backgroundColor: C.dangerBg, color: "#991B1B", padding: 10, borderRadius: R.md, overflow: "hidden", fontWeight: "600" },
  fab: { position: "absolute", right: 16, width: 54, height: 54, borderRadius: 27, backgroundColor: "#fff",
    alignItems: "center", justifyContent: "center", ...shadow, shadowOpacity: 0.15 },
  sheet: { position: "absolute", left: 12, right: 12, bottom: 14, backgroundColor: "#fff", borderRadius: R.xl, padding: 18, gap: 14,
    ...shadow, shadowOpacity: 0.18, shadowRadius: 20 },
  sheetIcon: { width: 46, height: 46, borderRadius: 14, alignItems: "center", justifyContent: "center" },
  sheetTitle: { fontSize: 18, fontWeight: "900", color: C.text },
  sheetSub: { fontSize: 13, color: C.muted, marginTop: 2 },
  facts: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  fact: { flexDirection: "row", alignItems: "center", gap: 5, backgroundColor: "#F1F5F9", paddingHorizontal: 10, paddingVertical: 6,
    borderRadius: R.pill },
  btn: { flex: 1, flexDirection: "row", gap: 8, alignItems: "center", justifyContent: "center", paddingVertical: 14, borderRadius: R.md },
  btnText: { color: "#fff", fontWeight: "800", fontSize: 15 },
});
