import { Ionicons } from "@expo/vector-icons";
import * as Location from "expo-location";
import { useRef, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { Gradient, IconCircle, T, tap } from "../../components/ui";
import { api, TOOL_LABEL } from "../../lib/api";
import { getDeviceId } from "../../lib/device";
import { C, GRAD, R } from "../../lib/theme";
import type { ChatMessage, ChatResponse } from "../../lib/types";

type Turn = ChatMessage & { steps?: ChatResponse["steps"]; ai_used?: boolean; blocked?: boolean };

const SUGGESTIONS: [string, string][] = [
  ["💊", "Norvadin oʻrniga arzonroq mahalliy analog bormi?"],
  ["📦", "Qayta ishlatilgan qutini qanday aniqlayman?"],
  ["📍", "Yaqin atrofda qaysi dorixonalar bor?"],
  ["🧾", "Dorixonadan qaysi hujjatni soʻrashim mumkin?"],
];

export default function Assistant() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const scroll = useRef<ScrollView>(null);

  async function ask(text: string) {
    if (!text.trim() || busy) return;
    tap();
    const next: Turn[] = [...turns, { role: "user", content: text.trim() }];
    setTurns(next);
    setInput("");
    setBusy(true);
    setError("");
    try {
      let lat: number | undefined;
      let lon: number | undefined;
      if (/yaqin|dorixona|qayerda/i.test(text)) {
        const perm = await Location.getForegroundPermissionsAsync();
        if (perm.granted) {
          const pos = await Location.getLastKnownPositionAsync();
          lat = pos?.coords.latitude;
          lon = pos?.coords.longitude;
        }
      }
      const r = await api.chat(next.map(({ role, content }) => ({ role, content })), await getDeviceId(), lat, lon);
      setTurns([...next, { role: "assistant", content: r.answer, steps: r.steps, ai_used: r.ai_used, blocked: r.blocked }]);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
      setTimeout(() => scroll.current?.scrollToEnd({ animated: true }), 100);
    }
  }

  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: C.bg }} behavior={Platform.OS === "ios" ? "padding" : undefined} keyboardVerticalOffset={90}>
      <ScrollView ref={scroll} contentContainerStyle={{ padding: 16, gap: 12 }}>
        {turns.length === 0 && (
          <>
            <Gradient colors={GRAD.violet} style={st.intro}>
              <View style={st.introIcon}><Ionicons name="sparkles" size={28} color={C.violet} /></View>
              <Text style={st.introTitle}>Salom! Men DoriIshonch AI yordamchisiman</Text>
              <Text style={st.introText}>Qutini tekshiraman, dori va analog topaman, zanjir tarixini va yaqin dorixonalarni koʻraman. Doza va davolash boʻyicha — faqat shifokor.</Text>
            </Gradient>
            <Text style={[T.small, { marginTop: 4 }]}>Masalan:</Text>
            {SUGGESTIONS.map(([e, q]) => (
              <Pressable key={q} onPress={() => ask(q)} style={({ pressed }) => [st.chip, pressed && { opacity: 0.7 }]}>
                <Text style={{ fontSize: 18 }}>{e}</Text>
                <Text style={[T.bold, { flex: 1, fontWeight: "500" }]}>{q}</Text>
                <Ionicons name="arrow-up-circle" size={22} color={C.violet} />
              </Pressable>
            ))}
          </>
        )}
        {turns.map((t, i) =>
          t.role === "user" ? (
            <View key={i} style={st.user}><Text style={{ color: "#fff", fontSize: 15 }}>{t.content}</Text></View>
          ) : (
            <View key={i} style={{ flexDirection: "row", gap: 8, maxWidth: "94%" }}>
              <IconCircle name="sparkles" size={30} color={C.violet} bg={C.violetBg} />
              <View style={{ flex: 1, gap: 4 }}>
                <View style={[st.bot, t.blocked && { backgroundColor: C.warnBg, borderColor: "#FDE68A" }]}>
                  <Text style={T.body}>{t.content}</Text>
                </View>
                {t.steps && t.steps.length > 0 && (
                  <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 4 }}>
                    {t.steps.map((s, k) => (
                      <View key={k} style={st.tool}><Ionicons name="construct" size={11} color={C.violet} /><Text style={st.toolText}>{TOOL_LABEL[s.tool] ?? s.tool}</Text></View>
                    ))}
                  </View>
                )}
              </View>
            </View>
          ),
        )}
        {busy && (
          <View style={{ flexDirection: "row", gap: 8, alignItems: "center" }}>
            <IconCircle name="sparkles" size={30} color={C.violet} bg={C.violetBg} />
            <View style={st.bot}><ActivityIndicator color={C.violet} /></View>
          </View>
        )}
        {error ? <Text style={{ color: C.danger }}>{error}</Text> : null}
      </ScrollView>
      <View style={st.inputRow}>
        <TextInput value={input} onChangeText={setInput} placeholder="Savolingizni yozing…" placeholderTextColor={C.faint}
          style={st.input} onSubmitEditing={() => ask(input)} returnKeyType="send" multiline />
        <Pressable onPress={() => ask(input)} style={[st.send, !input.trim() && { opacity: 0.4 }]} disabled={!input.trim()}>
          <Ionicons name="arrow-up" size={22} color="#fff" />
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

const st = StyleSheet.create({
  intro: { borderRadius: R.xl, padding: 20, gap: 8 },
  introIcon: { width: 52, height: 52, borderRadius: 16, backgroundColor: "#fff", alignItems: "center", justifyContent: "center", marginBottom: 4 },
  introTitle: { color: "#fff", fontSize: 20, fontWeight: "900" },
  introText: { color: "rgba(255,255,255,0.92)", lineHeight: 21 },
  chip: { flexDirection: "row", alignItems: "center", gap: 10, backgroundColor: "#fff", borderRadius: R.lg, borderWidth: 1, borderColor: C.border, padding: 14 },
  user: { alignSelf: "flex-end", backgroundColor: C.brand, borderRadius: 20, borderBottomRightRadius: 6, paddingVertical: 11, paddingHorizontal: 14, maxWidth: "85%" },
  bot: { backgroundColor: "#fff", borderRadius: 20, borderTopLeftRadius: 6, padding: 13, borderWidth: 1, borderColor: C.border },
  tool: { flexDirection: "row", alignItems: "center", gap: 3, backgroundColor: C.violetBg, borderRadius: R.pill, paddingHorizontal: 8, paddingVertical: 3 },
  toolText: { color: C.violet, fontSize: 11, fontWeight: "700" },
  inputRow: { flexDirection: "row", gap: 8, padding: 12, paddingBottom: 14, borderTopWidth: 1, borderTopColor: C.border, backgroundColor: "#fff", alignItems: "flex-end" },
  input: { flex: 1, backgroundColor: C.bg, borderRadius: 22, paddingHorizontal: 16, paddingVertical: 11, fontSize: 16, maxHeight: 110, color: C.text },
  send: { width: 44, height: 44, borderRadius: 22, backgroundColor: C.brand, alignItems: "center", justifyContent: "center" },
});
