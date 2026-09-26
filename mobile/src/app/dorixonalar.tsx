import * as Location from "expo-location";
import { useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { ActivityIndicator, Linking, Pressable, ScrollView, Text, View } from "react-native";
import { s as rs } from "../components/ResultView";
import { api } from "../lib/api";
import { setPharmacy } from "../lib/store";
import { C } from "../lib/theme";
import type { Participant } from "../lib/types";

const dist = (m: number) => (m < 1000 ? `${m} m` : `${(m / 1000).toFixed(1)} km`);

export default function Nearby() {
  const router = useRouter();
  const [rows, setRows] = useState<{ pharmacy: Participant; distance_m: number }[] | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);

  async function load() {
    setBusy(true);
    setError("");
    try {
      const perm = await Location.requestForegroundPermissionsAsync();
      if (!perm.granted) throw new Error("Joylashuvga ruxsat berilmadi. Telefon sozlamalarida ruxsat bering.");
      const pos = await Location.getCurrentPositionAsync({});
      setRows(await api.nearby(pos.coords.latitude, pos.coords.longitude));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function choose(p: Participant) {
    await setPharmacy(p);
    router.back();
  }

  function openMap(p: Participant) {
    const q = encodeURIComponent(`${p.name}, ${p.address || p.region}`);
    Linking.openURL(`http://maps.apple.com/?q=${q}`);
  }

  return (
    <ScrollView style={{ flex: 1, backgroundColor: C.bg }} contentContainerStyle={{ padding: 16, gap: 10, paddingBottom: 40 }}>
      <Text style={rs.body}>OpenStreetMap maʼlumotlari asosida 1,5 km radiusdagi dorixonalar. Dorixonani tanlasangiz, tekshiruvlar shu dorixonaga bogʻlanadi.</Text>
      {busy && <ActivityIndicator color={C.brand} />}
      {error ? (
        <View style={rs.card}>
          <Text style={{ color: C.danger }}>{error}</Text>
          <Pressable onPress={load}><Text style={{ color: C.brand, marginTop: 6, fontWeight: "600" }}>Qayta urinish</Text></Pressable>
        </View>
      ) : null}
      {rows && rows.length === 0 && <Text style={rs.body}>Yaqin atrofda dorixona topilmadi.</Text>}
      {rows?.map(({ pharmacy: p, distance_m }) => (
        <View key={p.id} style={rs.card}>
          <View style={{ flexDirection: "row", justifyContent: "space-between", gap: 8 }}>
            <Text style={[rs.bold, { flex: 1 }]}>{p.name}</Text>
            <Text style={rs.bold}>{dist(distance_m)}</Text>
          </View>
          <Text style={rs.small}>{p.address || p.region}</Text>
          {!p.license_ok && <Text style={{ color: C.danger, fontSize: 12 }}>⚠ Litsenziya muammosi qayd etilgan</Text>}
          <View style={{ flexDirection: "row", gap: 16, marginTop: 6 }}>
            <Pressable onPress={() => choose(p)}><Text style={{ color: C.brand, fontWeight: "700" }}>✓ Shu yerdaman</Text></Pressable>
            <Pressable onPress={() => openMap(p)}><Text style={{ color: C.info, fontWeight: "600" }}>🗺 Xaritada</Text></Pressable>
          </View>
        </View>
      ))}
    </ScrollView>
  );
}
