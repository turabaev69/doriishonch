import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { Text, View } from "react-native";
import { ResultView } from "../../components/ResultView";
import { Button, ErrorNote, Screen, T } from "../../components/ui";
import { fmt } from "../../lib/api";
import { runVerify } from "../../lib/scan";
import { getHistory, HistoryItem } from "../../lib/store";

export default function SavedResult() {
  const { id, fresh } = useLocalSearchParams<{ id: string; fresh?: string }>();
  const router = useRouter();
  const [item, setItem] = useState<HistoryItem | null | undefined>(undefined);
  const [error, setError] = useState("");

  useEffect(() => { getHistory().then((l) => setItem(l.find((x) => x.id === id) ?? null)); }, [id]);

  if (item === undefined) return null;
  if (!item) return <Screen><Text style={T.body}>Topilmadi.</Text></Screen>;

  // Tarixdan ochilganda ball banneri qayta koʻrsatilmaydi
  const r = fresh ? item.result : { ...item.result, reward: null };
  const canBuy = item.mode === "before" && !!item.code;

  return (
    <Screen>
      <Text style={T.small}>
        {fmt(item.at)} · {item.mode === "after" ? "Sotib olgandan keyin" : "Sotib olishdan oldin"}{item.pharmacy ? ` · ${item.pharmacy}` : ""}
      </Text>
      <ErrorNote text={error} />
      <ResultView
        r={r}
        onPurchase={canBuy ? async (price) => {
          setError("");
          try {
            const next = await runVerify(item.code, "after", price);
            router.replace({ pathname: "/natija/[id]", params: { id: next.id, fresh: "1" } });
          } catch (e) {
            setError((e as Error).message);
          }
        } : undefined}
      />
      <View style={{ gap: 10, marginTop: 4 }}>
        <Button title="Yana skanerlash" icon="scan" kind="secondary" onPress={() => router.replace({ pathname: "/skaner", params: { mode: "before" } })} />
      </View>
    </Screen>
  );
}
