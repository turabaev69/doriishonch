import { useRouter } from "expo-router";
import { useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { s as rs } from "../components/ResultView";
import { api } from "../lib/api";
import { C } from "../lib/theme";
import type { DrugBrief } from "../lib/types";
import { DrugRow } from "../components/DrugRow";

const EXAMPLES = ["Paratsetamol", "Amlodipin", "Norvadin", "Metformin", "Ibuprofen"];

export default function DrugSearch() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [rows, setRows] = useState<DrugBrief[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function search(text = q) {
    if (!text.trim()) return;
    setQ(text);
    setBusy(true);
    setError("");
    try {
      setRows((await api.search(text.trim())).results);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <ScrollView style={{ flex: 1, backgroundColor: C.bg }} contentContainerStyle={{ padding: 16, gap: 12 }} keyboardShouldPersistTaps="handled">
      <TextInput value={q} onChangeText={setQ} onSubmitEditing={() => search()} returnKeyType="search"
        placeholder="Dori nomi yoki taʼsir qiluvchi modda" style={[rs.input, { marginVertical: 0 }]} autoCorrect={false} />
      {!rows && (
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
          {EXAMPLES.map((e) => (
            <Pressable key={e} onPress={() => search(e)} style={st.chip}><Text>{e}</Text></Pressable>
          ))}
        </View>
      )}
      {busy && <ActivityIndicator color={C.brand} />}
      {error ? <Text style={{ color: C.danger }}>{error}</Text> : null}
      {rows && rows.length === 0 && <Text style={rs.body}>Hech narsa topilmadi. Imlo xatosi boʻlsa ham qidiruv ishlaydi — boshqacha yozib koʻring.</Text>}
      {rows && rows.length > 0 && (
        <View style={rs.card}>
          {rows.map((d) => <DrugRow key={d.id} d={d} onPress={() => router.push(`/dori/${d.id}`)} />)}
        </View>
      )}
      <Text style={rs.small}>Ishonch kartasi: roʻyxatdan oʻtish, GMP, sifat ogohlantirishlari va originalga tenglik dalillari — manbasi bilan. Ball yoki reyting berilmaydi.</Text>
    </ScrollView>
  );
}

const st = StyleSheet.create({
  chip: { backgroundColor: "#fff", borderRadius: 20, borderWidth: 1, borderColor: C.border, paddingVertical: 8, paddingHorizontal: 14 },
});
