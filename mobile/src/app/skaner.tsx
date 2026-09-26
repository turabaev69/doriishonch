import { Ionicons } from "@expo/vector-icons";
import { CameraView, useCameraPermissions } from "expo-camera";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useRef, useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Button, tap } from "../components/ui";
import { api } from "../lib/api";
import { runVerify } from "../lib/scan";
import { setPharmacy } from "../lib/store";
import { C, R } from "../lib/theme";
import type { Mode } from "../lib/types";

export default function Scanner() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { mode = "before" } = useLocalSearchParams<{ mode?: Mode }>();
  const [permission, requestPermission] = useCameraPermissions();
  const [torch, setTorch] = useState(false);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const locked = useRef(false);

  async function onScanned({ data }: { data: string }) {
    if (locked.current) return;
    locked.current = true;
    tap("success");
    // Dorixona kirishidagi QR: .../?dorixona=301
    const ph = data.match(/[?&]dorixona=(\d+)/);
    if (ph) {
      const p = (await api.pharmacies().catch(() => [])).find((x) => x.id === Number(ph[1]));
      if (p) {
        await setPharmacy(p);
        setMsg(`🏪 ${p.name} tanlandi. Endi dori qutisini skanerlang.`);
      } else setMsg("Dorixona topilmadi");
      setTimeout(() => { locked.current = false; }, 1200);
      return;
    }
    setBusy(true);
    try {
      const item = await runVerify(data, mode === "after" ? "after" : "before");
      router.replace({ pathname: "/natija/[id]", params: { id: item.id, fresh: "1" } });
    } catch (e) {
      setMsg((e as Error).message);
      setBusy(false);
      setTimeout(() => { locked.current = false; }, 1500);
    }
  }

  if (!permission) return <View style={st.black} />;
  if (!permission.granted)
    return (
      <View style={[st.black, { justifyContent: "center", padding: 28, gap: 16 }]}>
        <Ionicons name="camera" size={56} color="#fff" style={{ alignSelf: "center" }} />
        <Text style={st.title}>Kameraga ruxsat kerak</Text>
        <Text style={st.sub}>Dori qutisidagi kodni oʻqish uchun. Surat serverga yuborilmaydi — faqat kod matni.</Text>
        <Button title="Ruxsat berish" kind="white" onPress={requestPermission} />
        <Button title="Bekor qilish" kind="ghost" onPress={() => router.back()} style={{ backgroundColor: "transparent" }} />
      </View>
    );

  return (
    <View style={st.black}>
      <CameraView style={StyleSheet.absoluteFill} facing="back" enableTorch={torch}
        barcodeScannerSettings={{ barcodeTypes: ["datamatrix", "qr", "ean13"] }} onBarcodeScanned={busy ? undefined : onScanned} />
      <View style={[st.top, { paddingTop: insets.top + 8 }]}>
        <Pressable onPress={() => router.back()} style={st.round}><Ionicons name="close" size={24} color="#fff" /></Pressable>
        <View style={st.modePill}>
          <Text style={{ color: "#fff", fontWeight: "700" }}>{mode === "after" ? "Sotib oldim" : "Sotib olishdan oldin"}</Text>
        </View>
        <Pressable onPress={() => { tap(); setTorch(!torch); }} style={[st.round, torch && { backgroundColor: C.gold }]}>
          <Ionicons name={torch ? "flash" : "flash-outline"} size={22} color="#fff" />
        </Pressable>
      </View>
      <View style={st.center} pointerEvents="none">
        <View style={st.frame}>
          {[st.tl, st.tr, st.bl, st.br].map((c, i) => <View key={i} style={[st.corner, c]} />)}
        </View>
        <Text style={st.hint}>Kvadrat kodni ramkaga toʻgʻrilang</Text>
      </View>
      <View style={[st.bottom, { paddingBottom: insets.bottom + 24 }]}>
        {busy ? (
          <View style={st.toast}><ActivityIndicator color={C.brand} /><Text style={{ fontWeight: "700" }}>Tekshirilmoqda…</Text></View>
        ) : msg ? (
          <View style={st.toast}><Text style={{ fontWeight: "600", flex: 1 }}>{msg}</Text></View>
        ) : (
          <Text style={st.sub}>DataMatrix, QR yoki shtrix-kod. Qorongʻi boʻlsa, chiroqni yoqing.</Text>
        )}
      </View>
    </View>
  );
}

const SIZE = 250;
const st = StyleSheet.create({
  black: { flex: 1, backgroundColor: "#000" },
  title: { color: "#fff", fontSize: 22, fontWeight: "800", textAlign: "center" },
  sub: { color: "rgba(255,255,255,0.85)", textAlign: "center", fontSize: 14 },
  top: { position: "absolute", left: 0, right: 0, top: 0, flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: 16 },
  round: { width: 44, height: 44, borderRadius: 22, backgroundColor: "rgba(0,0,0,0.45)", alignItems: "center", justifyContent: "center" },
  modePill: { backgroundColor: "rgba(0,0,0,0.45)", borderRadius: R.pill, paddingHorizontal: 14, paddingVertical: 8 },
  center: { position: "absolute", top: 0, left: 0, right: 0, bottom: 0, alignItems: "center", justifyContent: "center", gap: 18 },
  frame: { width: SIZE, height: SIZE },
  corner: { position: "absolute", width: 44, height: 44, borderColor: "#fff" },
  tl: { top: 0, left: 0, borderTopWidth: 5, borderLeftWidth: 5, borderTopLeftRadius: 22 },
  tr: { top: 0, right: 0, borderTopWidth: 5, borderRightWidth: 5, borderTopRightRadius: 22 },
  bl: { bottom: 0, left: 0, borderBottomWidth: 5, borderLeftWidth: 5, borderBottomLeftRadius: 22 },
  br: { bottom: 0, right: 0, borderBottomWidth: 5, borderRightWidth: 5, borderBottomRightRadius: 22 },
  hint: { color: "#fff", fontWeight: "700", fontSize: 16, textShadowColor: "#000", textShadowRadius: 6 },
  bottom: { position: "absolute", left: 16, right: 16, bottom: 0, alignItems: "center" },
  toast: { backgroundColor: "#fff", borderRadius: R.md, padding: 14, flexDirection: "row", gap: 10, alignItems: "center", alignSelf: "stretch" },
});
