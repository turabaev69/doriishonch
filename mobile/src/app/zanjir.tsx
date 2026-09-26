import { useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { RefreshControl, ScrollView, Text, View } from "react-native";
import { s as rs } from "../components/ResultView";
import { api, fmt, KIND_LABEL } from "../lib/api";
import { C } from "../lib/theme";
import type { ChainStatus, LedgerEntry } from "../lib/types";

export default function Chain() {
  const [status, setStatus] = useState<ChainStatus | null>(null);
  const [blocks, setBlocks] = useState<LedgerEntry[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setBusy(true);
    setError("");
    try {
      const [st, bl] = await Promise.all([api.ledgerVerify(), api.ledgerLatest()]);
      setStatus(st);
      setBlocks(bl);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  return (
    <ScrollView style={{ flex: 1, backgroundColor: C.bg }} contentContainerStyle={{ padding: 16, gap: 10 }}
      refreshControl={<RefreshControl refreshing={busy} onRefresh={load} />}>
      <Text style={rs.body}>
        Har bir skanerlash zanjirga blok boʻlib yoziladi. Blok oldingi blokning SHA-256 hashini saqlaydi: birorta yozuvni
        oʻzgartirish butun zanjirni buzadi.
      </Text>
      {error ? <Text style={{ color: C.danger }}>{error}</Text> : null}
      {status && (
        <View style={[rs.card, { backgroundColor: status.ok ? C.okBg : C.dangerBg }]}>
          <Text style={[rs.h, { color: status.ok ? "#065f46" : "#991b1b" }]}>
            {status.ok ? `✓ Zanjir butun: ${status.blocks} blok` : `✕ Zanjir buzilgan: blok #${status.broken_at}`}
          </Text>
          <Text style={rs.hash} numberOfLines={1}>{status.last_hash}</Text>
        </View>
      )}
      {blocks.map((b) => (
        <View key={b.index} style={rs.card}>
          <Text style={[rs.bold, b.kind === "purchase" && { color: C.danger }]}>
            #{b.index} · {KIND_LABEL[b.kind] ?? b.kind}
          </Text>
          <Text style={rs.small}>
            {fmt(b.created_at)} · {b.serial} · {[b.pharmacy, b.region].filter(Boolean).join(", ")}
          </Text>
          <Text style={rs.hash} numberOfLines={1}>{b.hash}</Text>
          <Text style={rs.hash} numberOfLines={1}>← {b.prev_hash}</Text>
        </View>
      ))}
    </ScrollView>
  );
}
