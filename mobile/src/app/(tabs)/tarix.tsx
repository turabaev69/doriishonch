import { useFocusEffect, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { Alert, Pressable, StyleSheet, Text, View } from "react-native";
import { Button, Card, Empty, IconName, Pill, Row, Screen, Section, T } from "../../components/ui";
import { fmt } from "../../lib/api";
import { clearHistory, getHistory, HistoryItem, purchases } from "../../lib/store";
import { C, R, VERDICT } from "../../lib/theme";

export default function HistoryScreen() {
  const router = useRouter();
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [filter, setFilter] = useState<"all" | "danger">("all");

  useFocusEffect(useCallback(() => { getHistory().then(setItems); }, []));

  const mine = purchases(items);
  const bad = items.filter((i) => i.result.verdict === "danger");
  const shown = filter === "danger" ? bad : items;

  function clear() {
    Alert.alert("Tarixni tozalash", "Telefondagi tekshiruvlar oʻchiriladi. Zanjirdagi yozuvlar va ballar saqlanadi.", [
      { text: "Bekor", style: "cancel" },
      { text: "Tozalash", style: "destructive", onPress: async () => { await clearHistory(); setItems([]); } },
    ]);
  }

  if (items.length === 0)
    return (
      <Screen>
        <Empty icon="time" title="Hali tekshiruv yoʻq" text="Dorixonada qutini skanerlang — natijalar shu yerda saqlanadi."
          action={<Button title="Skanerlash" icon="scan" onPress={() => router.push({ pathname: "/skaner", params: { mode: "before" } })} style={{ marginTop: 8 }} />} />
      </Screen>
    );

  return (
    <Screen>
      <View style={{ flexDirection: "row", gap: 10 }}>
        <StatBox value={items.length} label="tekshiruv" color={C.brand} />
        <StatBox value={mine.length} label="mening dorim" color={C.info} />
        <StatBox value={bad.length} label="xavfli topildi" color={bad.length ? C.danger : C.muted} />
      </View>

      {mine.length > 0 && (
        <>
          <Section title="💊 Mening dorilarim" />
          <Card style={{ paddingVertical: 4 }}>
            {mine.map(({ item, daysLeft }, i) => {
              const d = item.result.drug;
              const tone = daysLeft == null ? C.muted : daysLeft < 0 ? C.danger : daysLeft <= 30 ? C.warn : C.ok;
              const text = daysLeft == null ? "—" : daysLeft < 0 ? "Muddati oʻtgan" : daysLeft <= 30 ? `${daysLeft} kun qoldi` : `${Math.round(daysLeft / 30)} oy qoldi`;
              return (
                <Row key={item.id} icon="medkit" iconColor={tone} iconBg={daysLeft != null && daysLeft <= 30 ? C.warnBg : C.brandLight}
                  title={d ? `${d.trade_name} ${d.strength}` : item.code.slice(0, 24)}
                  subtitle={`Partiya ${item.result.pack?.batch} · ${item.pharmacy ?? "dorixona koʻrsatilmagan"}`}
                  right={<Pill text={text} color={tone} bg={daysLeft != null && daysLeft < 0 ? C.dangerBg : "#F1F5F9"} />}
                  onPress={() => router.push(`/natija/${item.id}`)} last={i === mine.length - 1} />
              );
            })}
          </Card>
        </>
      )}

      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginTop: 6 }}>
        <Text style={T.h2}>Barcha tekshiruvlar</Text>
        <View style={st.seg}>
          {(["all", "danger"] as const).map((f) => (
            <Pressable key={f} onPress={() => setFilter(f)} style={[st.segBtn, filter === f && st.segOn]}>
              <Text style={[T.small, { fontWeight: "700" }, filter === f && { color: C.text }]}>{f === "all" ? "Hammasi" : "Xavfli"}</Text>
            </Pressable>
          ))}
        </View>
      </View>
      <Card style={{ paddingVertical: 4 }}>
        {shown.length === 0 && <Text style={[T.small, { padding: 12 }]}>Xavfli quti topilmagan. Ajoyib!</Text>}
        {shown.map((h, i) => {
          const v = VERDICT[h.result.verdict];
          return (
            <Row key={h.id} icon={v.ion as IconName} iconColor={v.bg} iconBg={v.soft} title={h.result.headline}
              subtitle={[h.result.drug?.trade_name, h.mode === "after" ? "sotib oldim" : null, h.pharmacy, fmt(h.at)].filter(Boolean).join(" · ")}
              onPress={() => router.push(`/natija/${h.id}`)} last={i === shown.length - 1} />
          );
        })}
      </Card>
      <Pressable onPress={clear}><Text style={{ color: C.muted, textAlign: "center" }}>Tarixni tozalash</Text></Pressable>
      <Text style={[T.tiny, { textAlign: "center" }]}>Tarix faqat shu telefonda saqlanadi.</Text>
    </Screen>
  );
}

function StatBox({ value, label, color }: { value: number; label: string; color: string }) {
  return (
    <View style={st.stat}>
      <Text style={[st.num, { color }]}>{value}</Text>
      <Text style={T.tiny}>{label}</Text>
    </View>
  );
}

const st = StyleSheet.create({
  stat: { flex: 1, backgroundColor: "#fff", borderRadius: R.lg, borderWidth: 1, borderColor: C.border, paddingVertical: 14, alignItems: "center" },
  num: { fontSize: 26, fontWeight: "900" },
  seg: { flexDirection: "row", backgroundColor: "#E2E8F0", borderRadius: R.pill, padding: 3 },
  segBtn: { paddingHorizontal: 12, paddingVertical: 5, borderRadius: R.pill },
  segOn: { backgroundColor: "#fff" },
});
