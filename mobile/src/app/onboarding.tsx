import { Ionicons } from "@expo/vector-icons";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { useRouter } from "expo-router";
import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Button, Gradient, IconName, tap } from "../components/ui";
import { C, GRAD, R } from "../lib/theme";

const SLIDES: { icon: IconName; title: string; text: string; colors: readonly [string, string] }[] = [
  { icon: "scan", title: "Sotib olishdan oldin skanerlang",
    text: "Qutidagi kvadrat kodni kameraga tuting. 3 soniyada bilasiz: dori roʻyxatdan oʻtganmi, bojxonadan kelganmi, quti oldin sotilmaganmi.",
    colors: GRAD.brand },
  { icon: "bag-check", title: "Sotib oldingizmi — belgilang",
    text: "Quti sizniki deb belgilanadi. Kimdir boʻsh qutini qayta toʻldirib sotsa, keyingi xaridor darhol ogohlantiriladi.",
    colors: ["#0B5F8C", "#1BA0D8"] },
  { icon: "star", title: "Ball yigʻing, mukofot oling",
    text: "Har bir tekshiruv, xarid va missiya uchun ball. Soxta dorini topsangiz — inspektor tasdiqlaganda katta mukofot.",
    colors: GRAD.gold },
  { icon: "shield-checkmark", title: "Anonim va xavfsiz",
    text: "Roʻyxatdan oʻtish shart emas. Ism, telefon va joylashuv serverda saqlanmaydi. Ilova tibbiy maslahat bermaydi.",
    colors: GRAD.violet },
];

export default function Onboarding() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [i, setI] = useState(0);
  const s = SLIDES[i];
  const last = i === SLIDES.length - 1;

  async function finish() {
    await AsyncStorage.setItem("doriishonch_onboarded", "1").catch(() => {});
    router.back();
  }

  return (
    <Gradient colors={s.colors} style={[st.wrap, { paddingTop: insets.top + 16, paddingBottom: insets.bottom + 24 }]}>
      <Pressable onPress={finish} style={{ alignSelf: "flex-end", padding: 8 }}>
        <Text style={st.skip}>Oʻtkazib yuborish</Text>
      </Pressable>
      <View style={st.center}>
        <View style={st.iconRing}><View style={st.icon}><Ionicons name={s.icon} size={64} color={C.text} /></View></View>
        <Text style={st.title}>{s.title}</Text>
        <Text style={st.text}>{s.text}</Text>
      </View>
      <View style={st.dots}>
        {SLIDES.map((_, k) => <View key={k} style={[st.dot, k === i && st.dotOn]} />)}
      </View>
      <Button title={last ? "Boshlash" : "Keyingi"} kind="white" size="lg" icon={last ? "checkmark" : "arrow-forward"}
        onPress={() => { tap(); last ? finish() : setI(i + 1); }} />
    </Gradient>
  );
}

const st = StyleSheet.create({
  wrap: { flex: 1, paddingHorizontal: 24 },
  skip: { color: "rgba(255,255,255,0.9)", fontWeight: "700" },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 18 },
  iconRing: { width: 170, height: 170, borderRadius: 85, backgroundColor: "rgba(255,255,255,0.18)", alignItems: "center", justifyContent: "center" },
  icon: { width: 124, height: 124, borderRadius: 62, backgroundColor: "#fff", alignItems: "center", justifyContent: "center" },
  title: { color: "#fff", fontSize: 28, fontWeight: "900", textAlign: "center", letterSpacing: -0.5 },
  text: { color: "rgba(255,255,255,0.92)", fontSize: 16, textAlign: "center", lineHeight: 23 },
  dots: { flexDirection: "row", justifyContent: "center", gap: 8, marginBottom: 20 },
  dot: { width: 8, height: 8, borderRadius: R.pill, backgroundColor: "rgba(255,255,255,0.4)" },
  dotOn: { width: 26, backgroundColor: "#fff" },
});
