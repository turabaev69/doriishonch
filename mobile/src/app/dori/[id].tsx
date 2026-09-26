import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { ActivityIndicator, Linking, Pressable, ScrollView, Text, View } from "react-native";
import { s as rs } from "../../components/ResultView";
import { api, fmt } from "../../lib/api";
import { C } from "../../lib/theme";
import type { AnalogsResponse, TrustCard } from "../../lib/types";
import { DrugRow, som } from "../../components/DrugRow";

const FACT: Record<string, [string, string]> = {
  ok: ["✓", C.ok], warn: ["!", C.warn], missing: ["–", C.muted], info: ["i", C.info],
};

export default function DrugCard() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [card, setCard] = useState<TrustCard | null>(null);
  const [an, setAn] = useState<AnalogsResponse | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setCard(null);
    Promise.all([api.drug(id), api.analogs(id)]).then(([c, a]) => { setCard(c); setAn(a); }).catch((e) => setError(e.message));
  }, [id]);

  if (error) return <Text style={{ color: C.danger, padding: 16 }}>{error}</Text>;
  if (!card) return <ActivityIndicator color={C.brand} style={{ marginTop: 40 }} />;
  const d = card.drug;

  return (
    <ScrollView style={{ flex: 1, backgroundColor: C.bg }} contentContainerStyle={{ padding: 16, gap: 12, paddingBottom: 40 }}>
      <View style={rs.card}>
        <Text style={{ fontSize: 22, fontWeight: "800", color: C.text }}>{d.trade_name} {d.strength}</Text>
        <Text style={rs.body}>{d.inn} · {d.form} · {d.pack_size}</Text>
        <Text style={rs.body}>{d.manufacturer.is_local ? "🇺🇿" : "🌍"} {d.manufacturer.name}, {d.manufacturer.country}</Text>
        <Text style={[rs.bold, { marginTop: 4 }]}>{som(d.price_uzs)}{d.prescription_only ? " · 📝 retsept bilan" : ""}</Text>
        {d.is_demo && <Text style={rs.small}>Demo maʼlumot</Text>}
      </View>

      <View style={rs.card}>
        <Text style={rs.h}>Ishonch kartasi</Text>
        {card.facts.map((f) => {
          const [icon, color] = FACT[f.status] ?? FACT.info;
          return (
            <View key={f.key} style={{ flexDirection: "row", gap: 10, paddingVertical: 8, borderTopWidth: 1, borderTopColor: C.border }}>
              <Text style={{ color, fontWeight: "800", width: 16 }}>{icon}</Text>
              <View style={{ flex: 1 }}>
                <Text style={rs.bold}>{f.label}</Text>
                <Text style={rs.body}>{f.text}</Text>
                <Text style={rs.small}>
                  {f.provided_by_manufacturer ? "Ishlab chiqaruvchi maʼlumoti · " : ""}
                  {f.updated_at ? `yangilangan ${fmt(f.updated_at).slice(0, 10)}` : ""}
                </Text>
                {f.source_url && (
                  <Pressable onPress={() => Linking.openURL(f.source_url!)}>
                    <Text style={{ color: C.brand, fontSize: 12 }}>Manba ↗</Text>
                  </Pressable>
                )}
              </View>
            </View>
          );
        })}
        <Text style={[rs.small, { marginTop: 6 }]}>{card.disclaimer}</Text>
      </View>

      {an && an.analogs.length > 0 && (
        <View style={rs.card}>
          <Text style={rs.h}>Analoglar (bir xil modda va doza)</Text>
          <Text style={rs.small}>{an.note}</Text>
          {an.analogs.map((a) => (
            <DrugRow key={a.drug.id} d={a.drug} onPress={() => router.push(`/dori/${a.drug.id}`)}
              extra={`${a.price_diff_pct > 0 ? "+" : ""}${a.price_diff_pct}%${a.has_valid_gmp ? " · GMP" : ""}${a.quality_alert_count ? " · ⚠" : ""}`} />
          ))}
        </View>
      )}
    </ScrollView>
  );
}
