import { Pressable, StyleSheet, Text, View } from "react-native";
import { C } from "../lib/theme";
import type { DrugBrief } from "../lib/types";
import { s as rs } from "./ResultView";

export const som = (n: number) => `${n.toLocaleString("ru-RU").replace(/,/g, " ")} soʻm`;

export function DrugRow({ d, onPress, extra }: { d: DrugBrief; onPress: () => void; extra?: string }) {
  return (
    <Pressable onPress={onPress} style={st.row}>
      <Text style={{ fontSize: 22 }}>{d.manufacturer.is_local ? "🇺🇿" : "🌍"}</Text>
      <View style={{ flex: 1 }}>
        <Text style={rs.bold}>{d.trade_name} {d.strength}</Text>
        <Text style={rs.small}>{d.inn} · {d.form} · {d.manufacturer.name}, {d.manufacturer.country}</Text>
      </View>
      <View style={{ alignItems: "flex-end" }}>
        <Text style={rs.bold}>{som(d.price_uzs)}</Text>
        {extra ? <Text style={rs.small}>{extra}</Text> : d.prescription_only ? <Text style={rs.small}>📝 retsept</Text> : null}
      </View>
    </Pressable>
  );
}

const st = StyleSheet.create({
  row: { flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: C.border },
});
