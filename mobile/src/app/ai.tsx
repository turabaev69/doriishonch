import { Ionicons } from "@expo/vector-icons";
import { Asset } from "expo-asset";
import * as ImagePicker from "expo-image-picker";
import { useEffect, useState } from "react";
import { Image, Pressable, StyleSheet, Text, View } from "react-native";
import { Button, Card, ErrorNote, Pill, Screen, Section, T, tap } from "../components/ui";
import { api } from "../lib/api";
import type { PackResult } from "../lib/packnet";
import { checkPackaging, getPackNet } from "../lib/packnetClient";
import { C, R } from "../lib/theme";
import type { MlStatus } from "../lib/types";

// Demo qutilar suratlari (ml/packnet/make_samples.py) — model ularni hech qachon oʻqitishda koʻrmagan
const SAMPLES = [
  { key: "norvadin-asl", label: "Norvadin · asl", gtin: "04780000007919", src: require("../../assets/demo-boxes/norvadin-asl.jpg") },
  { key: "norvadin-qalbaki", label: "Norvadin · qalbaki", gtin: "04780000007919", src: require("../../assets/demo-boxes/norvadin-qalbaki.jpg") },
  { key: "amoxibos-asl", label: "Amoxibos · asl", gtin: "04780000190056", src: require("../../assets/demo-boxes/amoxibos-asl.jpg") },
  { key: "amoxibos-qalbaki", label: "Amoxibos · qalbaki", gtin: "04780000190056", src: require("../../assets/demo-boxes/amoxibos-qalbaki.jpg") },
  { key: "metgan-asl", label: "Metgan · asl", gtin: "04780000047514", src: require("../../assets/demo-boxes/metgan-asl.jpg") },
  { key: "metgan-qalbaki", label: "Metgan · qalbaki", gtin: "04780000047514", src: require("../../assets/demo-boxes/metgan-qalbaki.jpg") },
  { key: "zartramol-asl", label: "Zartramol · asl", gtin: "04780000253408", src: require("../../assets/demo-boxes/zartramol-asl.jpg") },
  { key: "boshqa", label: "Notanish quti", gtin: "", src: require("../../assets/demo-boxes/boshqa.jpg") },
];

const VERDICT: Record<PackResult["verdict"], { fg: string; bg: string; icon: keyof typeof Ionicons.glyphMap }> = {
  asl: { fg: "#166534", bg: C.okBg, icon: "checkmark-circle" },
  farq: { fg: "#991B1B", bg: C.dangerBg, icon: "alert-circle" },
  boshqa: { fg: "#92400E", bg: C.warnBg, icon: "swap-horizontal" },
  tanilmadi: { fg: C.muted, bg: "#F1F5F9", icon: "help-circle" },
};

export default function AiScreen() {
  const [status, setStatus] = useState<MlStatus | null>(null);
  const [picked, setPicked] = useState<string | null>(null);
  const [uri, setUri] = useState<string | null>(null);
  const [res, setRes] = useState<PackResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.mlStatus().then(setStatus).catch(() => {});
  }, []);

  async function run(u: string, w: number, h: number, gtin: string | null, key: string) {
    setBusy(true);
    setErr("");
    setRes(null);
    setPicked(key);
    setUri(u);
    try {
      const r = await checkPackaging(u, w, h, gtin);
      setRes(r);
      tap(r.verdict === "asl" ? "success" : "warning");
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function sample(s: (typeof SAMPLES)[number]) {
    const a = Asset.fromModule(s.src);
    await a.downloadAsync();
    await run(a.localUri || a.uri, a.width || 256, a.height || 256, s.gtin || null, s.key);
  }

  async function own() {
    const shot = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], quality: 0.8 });
    const a = shot.canceled ? null : shot.assets[0];
    if (a) await run(a.uri, a.width, a.height, null, "own");
  }

  const card = getPackNet().card;
  const pm = (status?.packnet?.metrics_val_synthetic ?? (card as { metrics_val_synthetic?: Record<string, unknown> }).metrics_val_synthetic ?? {}) as Record<string, number>;
  const h = status?.risk?.metrics.synthetic_holdout;
  const v = res ? VERDICT[res.verdict] : null;

  return (
    <Screen>
      <Card tone="violet">
        <View style={{ flexDirection: "row", gap: 10, alignItems: "center" }}>
          <Ionicons name="scan-circle" size={24} color={C.violet} />
          <Text style={[T.h3, { flex: 1 }]}>Qadoq modeli (PackNet)</Text>
          <Pill text="Internetsiz" icon="airplane" color={C.violet} bg="#fff" />
        </View>
        <Text style={T.small}>Quti suratidan qaysi dori ekanini va asl dizayndan farqini topadi. Telefoningizda ishlaydi.</Text>
        <View style={st.stats}>
          <Stat label="Dorini taniydi" value={pct(pm.product_acc_known)} />
          <Stat label="Qalbakini topadi" value={pct(pm.fake_recall_at_threshold)} />
          <Stat label="Asl qutiga xato" value={pct(pm.genuine_flagged_at_threshold)} muted />
        </View>
      </Card>

      <Section title="Sinab koʻring" />
      <View style={st.grid}>
        {SAMPLES.map((s) => (
          <Pressable key={s.key} onPress={() => sample(s)} disabled={busy} style={[st.tile, picked === s.key && { borderColor: C.violet }]}>
            <Image source={s.src} style={st.img} />
            <Text style={st.tileText} numberOfLines={1}>{s.label}</Text>
          </Pressable>
        ))}
      </View>
      <Button title="Oʻz suratingizni tanlash" icon="images" kind="dark" onPress={own} busy={busy} style={{ backgroundColor: C.violet }} />
      <ErrorNote text={err} />

      {res && v && (
        <Card>
          <View style={{ flexDirection: "row", gap: 12 }}>
            {uri && <Image source={{ uri }} style={{ width: 72, height: 72, borderRadius: 12 }} />}
            <View style={{ flex: 1, gap: 4 }}>
              <View style={[st.badge, { backgroundColor: v.bg }]}>
                <Ionicons name={v.icon} size={16} color={v.fg} />
                <Text style={{ color: v.fg, fontWeight: "800" }}>{res.title}</Text>
              </View>
              <Text style={T.small}>{res.text}</Text>
              <Text style={T.tiny}>
                Oʻxshash: {res.product.name} ({Math.round(res.product.prob * 100)}%) · farq ehtimoli {Math.round(res.fake_prob * 100)}% · {res.ms} ms
              </Text>
            </View>
          </View>
        </Card>
      )}

      {h && status?.risk && (
        <>
          <Section title="Skan xavf modeli" />
          <Card>
            <Text style={T.small}>Har bir skan uchun qalbaki boʻlish ehtimoli: quti tarixi, narx, dorixona va partiya signallari.</Text>
            <View style={st.stats}>
              <Stat label="Model (AUC)" value={h.roc_auc.toFixed(2)} />
              <Stat label="Faqat qoidalar" value={h.rules_only_roc_auc.toFixed(2)} muted />
            </View>
            <Text style={T.tiny}>
              {status.risk.n_real} ta inspektor tasdigʻidan oʻrgangan · har {status.retrain_every} ta yangisidan keyin oʻzi yangilanadi
            </Text>
          </Card>
        </>
      )}
      <Text style={[T.tiny, { textAlign: "center" }]}>{card.notes}</Text>
    </Screen>
  );
}

const pct = (v: unknown) => (typeof v === "number" ? `${Math.round(v * 100)}%` : "—");

function Stat({ label, value, muted }: { label: string; value: string; muted?: boolean }) {
  return (
    <View style={st.stat}>
      <Text style={{ fontSize: 20, fontWeight: "800", color: muted ? C.faint : C.text }}>{value}</Text>
      <Text style={{ fontSize: 11, color: C.muted, textAlign: "center" }}>{label}</Text>
    </View>
  );
}

const st = StyleSheet.create({
  stats: { flexDirection: "row", gap: 8, marginTop: 8 },
  stat: { flex: 1, backgroundColor: "#fff", borderRadius: R.md, paddingVertical: 10, alignItems: "center" },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  tile: { width: "23%", borderRadius: R.sm, borderWidth: 2, borderColor: "transparent", overflow: "hidden", backgroundColor: "#fff" },
  img: { width: "100%", aspectRatio: 1 },
  tileText: { fontSize: 10, color: C.muted, paddingHorizontal: 4, paddingVertical: 3 },
  badge: { flexDirection: "row", alignItems: "center", gap: 6, alignSelf: "flex-start", paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999 },
});
