import { Ionicons } from "@expo/vector-icons";
import AsyncStorage from "@react-native-async-storage/async-storage";
import * as ImagePicker from "expo-image-picker";
import { useFocusEffect, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { ActivityIndicator, Modal, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Button, Card, ErrorNote, Gradient, IconCircle, IconName, Pill, Row, Section, T, tap, u } from "../../components/ui";
import { api, fmt, getServer } from "../../lib/api";
import { getDeviceId } from "../../lib/device";
import { runVerify, runVerifyImage } from "../../lib/scan";
import { getHistory, getPharmacy, HistoryItem, setPharmacy } from "../../lib/store";
import { C, R, VERDICT } from "../../lib/theme";
import type { Mission, Mode, Participant, Wallet } from "../../lib/types";

export default function Home() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [mode, setMode] = useState<Mode>("before");
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [mission, setMission] = useState<Mission | null>(null);
  const [pharmacy, setPh] = useState<Participant | null>(null);
  const [recent, setRecent] = useState<HistoryItem[]>([]);
  const [noServer, setNoServer] = useState(false);
  const [manualOpen, setManualOpen] = useState(false);
  const [manual, setManual] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useFocusEffect(
    useCallback(() => {
      AsyncStorage.getItem("doriishonch_onboarded").then((v) => { if (!v) router.push("/onboarding"); }).catch(() => {});
      getPharmacy().then(setPh);
      getHistory().then((h) => setRecent(h.slice(0, 3)));
      getServer().then(async (srv) => {
        setNoServer(!srv);
        if (!srv) return;
        const id = await getDeviceId();
        api.wallet(id).then(setWallet).catch(() => {});
        api.missions(id).then((m) => setMission(m.find((x) => !x.done) ?? null)).catch(() => {});
      });
    }, [router]),
  );

  async function open(item: HistoryItem) {
    router.push({ pathname: "/natija/[id]", params: { id: item.id, fresh: "1" } });
  }

  async function fromPhoto(source: "camera" | "library") {
    setError("");
    const perm = source === "camera" ? await ImagePicker.requestCameraPermissionsAsync() : await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) return setError("Ruxsat berilmadi. Telefon sozlamalarida ruxsat bering.");
    const pick = source === "camera"
      ? await ImagePicker.launchCameraAsync({ quality: 0.8 })
      : await ImagePicker.launchImageLibraryAsync({ quality: 0.8, mediaTypes: ["images"] });
    if (pick.canceled || !pick.assets[0]) return;
    setBusy(true);
    try {
      open(await runVerifyImage(pick.assets[0].uri, mode));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function submitManual() {
    if (!manual.trim()) return;
    setBusy(true);
    setError("");
    try {
      const item = await runVerify(manual.trim(), mode);
      setManualOpen(false);
      setManual("");
      open(item);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const actions: [IconName, string, string, () => void][] = [
    ["camera", "Surat", C.violet, () => fromPhoto("camera")],
    ["keypad", "Kod yozish", C.info, () => setManualOpen(true)],
    ["map", "Xarita", C.brand, () => router.push("/xarita")],
  ];

  return (
    <View style={{ flex: 1, backgroundColor: C.bg }}>
      <ScrollView contentContainerStyle={{ paddingBottom: 40 }} keyboardShouldPersistTaps="handled">
        <Gradient style={[st.hero, { paddingTop: insets.top + 12 }]}>
          <View style={st.heroTop}>
            <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
              <View style={st.logo}><Ionicons name="shield-checkmark" size={18} color={C.brand} /></View>
              <Text style={st.brand}>DoriIshonch</Text>
            </View>
            <Pressable onPress={() => router.push("/ballar")} style={st.points}>
              <Ionicons name="star" size={15} color={C.gold} />
              <Text style={st.pointsText}>{wallet ? wallet.points : "—"}</Text>
            </Pressable>
          </View>

          <Text style={st.heroTitle}>Dori haqiqiymi?</Text>
          <Text style={st.heroSub}>Qutidagi kvadrat kodni skanerlang — javob 3 soniyada.</Text>

          <Pressable onPress={() => { tap(); router.push({ pathname: "/skaner", params: { mode: "before" } }); }}
            style={({ pressed }) => [st.scanBtn, pressed && { transform: [{ scale: 0.98 }] }]} disabled={noServer}>
            <Ionicons name="scan" size={34} color={C.brand} />
            <Text style={st.scanTitle}>Skanerlash</Text>
          </Pressable>
        </Gradient>

        <View style={{ padding: 16, gap: 14 }}>
          {noServer && (
            <Card tone="gold" onPress={() => router.push("/sozlamalar")}>
              <Row icon="cloud-offline" iconColor={C.warn} iconBg="#fff" title="Serverga ulanmagan" subtitle="Koʻproq → Server manzili" last />
            </Card>
          )}
          <ErrorNote text={error} />

          <View style={st.grid}>
            {actions.map(([icon, title, color, fn]) => (
              <Pressable key={title} onPress={() => { tap(); fn(); }} style={({ pressed }) => [st.action, pressed && { opacity: 0.8 }]}>
                <IconCircle name={icon} size={48} color={color} bg={color + "18"} />
                <Text style={st.actionText}>{title}</Text>
              </Pressable>
            ))}
          </View>

          <Card onPress={() => router.push("/xarita")}>
            <Row icon="location" title={pharmacy ? pharmacy.name : "Dorixonani tanlang"}
              subtitle={pharmacy ? pharmacy.region : "Xaritadan · +5 ball"}
              right={pharmacy ? (
                <Pressable onPress={() => { setPharmacy(null); setPh(null); }} hitSlop={10}>
                  <Ionicons name="close-circle" size={22} color={C.faint} />
                </Pressable>
              ) : undefined} last />
          </Card>

          {mission && (
            <Pressable onPress={() => router.push("/xarita")}>
              <Gradient colors={["#5B47D6", "#8B7CF6"]} style={st.mission}>
                <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
                  <Text style={st.missionTag}>⭐ MISSIYA</Text>
                  <Text style={st.missionPts}>+{mission.points} ball</Text>
                </View>
                <Text style={st.missionTitle}>{mission.pharmacy}</Text>
                <Text style={st.missionSub}>Shu dorixonada bitta dorini tekshiring</Text>
              </Gradient>
            </Pressable>
          )}

          {recent.length > 0 && (
            <>
              <Section title="Oxirgi tekshiruvlar" action="Hammasi" onAction={() => router.push("/tarix")} />
              <Card style={{ paddingVertical: 4 }}>
                {recent.map((h, i) => {
                  const v = VERDICT[h.result.verdict];
                  return (
                    <Row key={h.id} icon={v.ion as IconName} iconColor={v.bg} iconBg={v.soft} title={h.result.drug?.trade_name || h.result.headline}
                      subtitle={`${v.label} · ${fmt(h.at)}`}
                      onPress={() => router.push(`/natija/${h.id}`)} last={i === recent.length - 1} />
                  );
                })}
              </Card>
            </>
          )}

          <View style={st.links}>
            <Pressable onPress={() => router.push("/yordamchi")} style={st.link}>
              <Ionicons name="chatbubbles" size={18} color={C.violet} />
              <Text style={st.linkText}>Savol berish</Text>
            </Pressable>
            <Pressable onPress={() => router.push("/demo")} style={st.link}>
              <Ionicons name="flask" size={18} color={C.gold} />
              <Text style={st.linkText}>Demo qutilar</Text>
            </Pressable>
          </View>
        </View>
      </ScrollView>

      <Modal visible={manualOpen} transparent animationType="slide" onRequestClose={() => setManualOpen(false)}>
        <Pressable style={st.backdrop} onPress={() => setManualOpen(false)} />
        <View style={[st.sheet, { paddingBottom: insets.bottom + 20 }]}>
          <View style={st.handle} />
          <Text style={T.h2}>Kodni kiriting</Text>
          <Text style={T.small}>Kvadrat kod ostidagi yozuvni koʻchiring, masalan: (01)0478…(21)…</Text>
          <TextInput value={manual} onChangeText={setManual} placeholder="(01)0478…(21)…" autoCapitalize="characters"
            autoFocus style={u.input} onSubmitEditing={submitManual} />
          <Button title="Tekshirish" icon="shield-checkmark" busy={busy} onPress={submitManual} />
        </View>
      </Modal>

      {busy && !manualOpen && (
        <View style={st.overlay}>
          <View style={st.overlayBox}>
            <ActivityIndicator color={C.brand} size="large" />
            <Text style={T.bold}>Tekshirilmoqda…</Text>
          </View>
        </View>
      )}
    </View>
  );
}

const st = StyleSheet.create({
  hero: { paddingHorizontal: 20, paddingBottom: 28, borderBottomLeftRadius: 32, borderBottomRightRadius: 32 },
  heroTop: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 18 },
  logo: { width: 30, height: 30, borderRadius: 9, backgroundColor: "#fff", alignItems: "center", justifyContent: "center" },
  brand: { color: "#fff", fontWeight: "800", fontSize: 18 },
  points: { flexDirection: "row", alignItems: "center", gap: 5, backgroundColor: "rgba(255,255,255,0.2)", paddingHorizontal: 12, paddingVertical: 7, borderRadius: R.pill },
  pointsText: { color: "#fff", fontWeight: "800", fontSize: 15 },
  pointsLevel: { fontSize: 14 },
  heroTitle: { color: "#fff", fontSize: 34, fontWeight: "900", letterSpacing: -0.8, lineHeight: 40 },
  heroSub: { color: "rgba(255,255,255,0.88)", fontSize: 15, marginTop: 8 },
  seg: { flex: 1, paddingVertical: 10, borderRadius: R.pill, alignItems: "center" },
  segOn: { backgroundColor: "#fff" },
  segText: { color: "#fff", fontWeight: "700", fontSize: 14 },
  scanBtn: { marginTop: 20, backgroundColor: "#fff", borderRadius: R.xl, paddingVertical: 22, flexDirection: "row", alignItems: "center",
    justifyContent: "center", gap: 12,
    shadowColor: "#000", shadowOpacity: 0.15, shadowRadius: 16, shadowOffset: { width: 0, height: 8 }, elevation: 6 },
  scanIcon: { width: 58, height: 58, borderRadius: 18, backgroundColor: C.brand, alignItems: "center", justifyContent: "center" },
  scanTitle: { fontSize: 24, fontWeight: "900", color: C.text },
  scanSub: { fontSize: 13, color: C.muted, marginTop: 2 },
  grid: { flexDirection: "row", gap: 12 },
  action: { flex: 1, backgroundColor: "#fff", borderRadius: R.lg, paddingVertical: 16, gap: 8, alignItems: "center",
    borderWidth: 1, borderColor: C.border },
  actionText: { fontWeight: "800", fontSize: 14, color: C.text },
  links: { flexDirection: "row", gap: 12 },
  link: { flex: 1, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, paddingVertical: 14,
    backgroundColor: "#fff", borderRadius: R.lg, borderWidth: 1, borderColor: C.border },
  linkText: { fontWeight: "700", color: C.text },
  mission: { borderRadius: R.lg, padding: 16, gap: 6 },
  missionTag: { color: "#fff", fontWeight: "800", fontSize: 11, letterSpacing: 1 },
  missionPts: { color: "#fff", fontWeight: "900" },
  missionTitle: { color: "#fff", fontWeight: "800", fontSize: 17 },
  missionSub: { color: "rgba(255,255,255,0.85)", fontSize: 13 },
  backdrop: { flex: 1, backgroundColor: "rgba(15,27,42,0.4)" },
  sheet: { backgroundColor: "#fff", borderTopLeftRadius: 28, borderTopRightRadius: 28, padding: 20, gap: 12 },
  handle: { alignSelf: "center", width: 44, height: 5, borderRadius: 3, backgroundColor: C.border, marginBottom: 4 },
  overlay: { position: "absolute", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(15,27,42,0.35)", alignItems: "center", justifyContent: "center" },
  overlayBox: { backgroundColor: "#fff", borderRadius: R.lg, padding: 24, alignItems: "center", gap: 12 },
});
