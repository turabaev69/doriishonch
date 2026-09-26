import { Ionicons } from "@expo/vector-icons";
import { useFocusEffect, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { Alert, Modal, Pressable, RefreshControl, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Button, Card, Empty, ErrorNote, Gradient, IconCircle, Pill, Progress, Row, Section, T, tap, u } from "../../components/ui";
import { api, fmt } from "../../lib/api";
import { getDeviceId } from "../../lib/device";
import { C, GRAD, R } from "../../lib/theme";
import type { LeaderRow, Mission, RewardItem, Wallet } from "../../lib/types";

const RULE_ICON: Record<string, string> = { scan: "scan", pharmacy: "storefront", purchase: "bag-check", mission: "flag",
  catch: "shield", report: "megaphone", bounty: "trophy" };

export default function Points() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [w, setW] = useState<Wallet | null>(null);
  const [missions, setMissions] = useState<Mission[]>([]);
  const [board, setBoard] = useState<LeaderRow[]>([]);
  const [items, setItems] = useState<RewardItem[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [nickOpen, setNickOpen] = useState(false);
  const [nick, setNick] = useState("");
  const [nickErr, setNickErr] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const id = await getDeviceId();
      const [a, b, c, d] = await Promise.all([api.wallet(id), api.missions(id), api.leaderboard(id), api.catalog()]);
      setW(a); setMissions(b); setBoard(c); setItems(d.items);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);
  useFocusEffect(useCallback(() => { load(); }, [load]));

  async function redeem(item: RewardItem) {
    Alert.alert(item.title, `${item.points} ball sarflanadi. Davom etamizmi?`, [
      { text: "Bekor", style: "cancel" },
      { text: "Almashtirish", onPress: async () => {
        try {
          const r = await api.redeem(await getDeviceId(), item.key);
          tap("success");
          Alert.alert("🎉 Tayyor!", `Kod: ${r.code}\n\n${r.note}`);
          load();
        } catch (e) {
          Alert.alert("Boʻlmadi", (e as Error).message);
        }
      } },
    ]);
  }

  async function saveNick() {
    setNickErr("");
    try {
      await api.nickname(await getDeviceId(), nick);
      setNickOpen(false);
      load();
    } catch (e) {
      setNickErr((e as Error).message);
    }
  }

  const top = board.filter((r) => r.rank <= 10 || r.me);

  return (
    <View style={{ flex: 1, backgroundColor: C.bg }}>
      <ScrollView contentContainerStyle={{ paddingBottom: 40 }} refreshControl={<RefreshControl refreshing={loading} onRefresh={load} />}>
        <Gradient colors={GRAD.brand} style={[st.head, { paddingTop: insets.top + 14 }]}>
          <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
            <Pressable onPress={() => { setNick(w?.has_nickname ? w.nickname : ""); setNickOpen(true); }} style={{ flexDirection: "row", gap: 6, alignItems: "center" }}>
              <Text style={st.nick}>{w?.nickname ?? "…"}</Text>
              <Ionicons name="pencil" size={14} color="rgba(255,255,255,0.8)" />
            </Pressable>
            {w?.rank ? <View style={st.rank}><Ionicons name="trophy" size={13} color={C.gold} /><Text style={st.rankText}>#{w.rank}</Text></View> : null}
          </View>
          <View style={{ flexDirection: "row", alignItems: "flex-end", gap: 8, marginTop: 10 }}>
            <Ionicons name="star" size={34} color={C.gold} style={{ marginBottom: 6 }} />
            <Text style={st.big}>{w?.points ?? 0}</Text>
            <Text style={st.bigSub}>ball</Text>
          </View>
          {w && (
            <>
              <Text style={st.level}>{w.level.icon} {w.level.name}{w.level.next_name ? `  →  ${w.level.next_name} (${w.level.next_min})` : "  ·  eng yuqori daraja"}</Text>
              <Progress value={w.level.progress} />
              <View style={st.stats}>
                <Stat icon="flame" value={`${w.streak}`} label="kun ketma-ket" />
                <Stat icon="today" value={`${w.today.earned}/${w.today.cap}`} label="bugun" />
                <Stat icon="hourglass" value={`${w.pending}`} label="kutilmoqda" />
              </View>
            </>
          )}
        </Gradient>

        <View style={{ padding: 16, gap: 14 }}>
          <ErrorNote text={error} />
          {w?.flagged && <ErrorNote text="Hamyoningizda gʻayrioddiy faollik aniqlandi: ballar vaqtincha toʻxtatilgan." />}

          <Section title="🚩 Haftalik missiyalar" />
          <Text style={[T.small, { marginTop: -8 }]}>Tekshiruvlar kam boʻlgan dorixonalarda skanerlang — soxta dorilarni birga topamiz.</Text>
          {missions.length === 0 && <Card><Text style={T.small}>Hozircha missiya yoʻq.</Text></Card>}
          {missions.map((m) => (
            <Card key={m.id} style={m.done ? { opacity: 0.7 } : undefined} onPress={() => router.push("/xarita")}>
              <View style={{ flexDirection: "row", gap: 12, alignItems: "center" }}>
                <IconCircle name={m.done ? "checkmark" : "flag"} color={m.done ? C.ok : C.violet} bg={m.done ? C.okBg : C.violetBg} />
                <View style={{ flex: 1 }}>
                  <Text style={T.bold}>{m.pharmacy}</Text>
                  <Text style={T.small}>{m.region}{m.address ? ` · ${m.address}` : ""} · bu hafta {m.scanners_this_week} kishi tekshirdi</Text>
                </View>
                {m.done ? <Pill text="Bajarildi" color={C.ok} bg={C.okBg} /> : <Pill text={`+${m.points}`} icon="star" color="#B45309" bg={C.goldBg} />}
              </View>
            </Card>
          ))}

          <Section title="Nishonlar" />
          <View style={st.badges}>
            {(w?.badges ?? []).map((b) => (
              <View key={b.key} style={[st.badge, !b.earned && { opacity: 0.4 }]}>
                <Text style={{ fontSize: 30 }}>{b.icon}</Text>
                <Text style={[T.bold, { fontSize: 13, textAlign: "center" }]}>{b.title}</Text>
                <Text style={[T.tiny, { textAlign: "center" }]} numberOfLines={3}>{b.description}</Text>
              </View>
            ))}
          </View>

          <Section title="Mukofotlar" />
          {items.map((it) => {
            const enough = (w?.points ?? 0) >= it.points;
            return (
              <Card key={it.key}>
                <View style={{ flexDirection: "row", gap: 12, alignItems: "center" }}>
                  <View style={st.gift}><Text style={{ fontSize: 26 }}>{it.icon}</Text></View>
                  <View style={{ flex: 1 }}>
                    <Text style={T.bold}>{it.title}</Text>
                    <Text style={T.small}>{it.partner}</Text>
                  </View>
                  <Button title={`${it.points}`} icon="star" size="sm" kind={enough ? "gold" : "secondary"} disabled={!enough} onPress={() => redeem(it)} />
                </View>
                {!enough && w && <Progress value={w.points / it.points} color={C.gold} track="#F1F5F9" height={6} />}
              </Card>
            );
          })}
          {w && w.redemptions.length > 0 && (
            <Card tone="gold">
              <Text style={T.h3}>Mening kodlarim</Text>
              {w.redemptions.map((r) => (
                <Row key={r.code} icon="ticket" iconColor="#B45309" iconBg="#fff" title={r.title} subtitle={`${r.code} · ${fmt(r.at)}`} last />
              ))}
            </Card>
          )}

          <Section title="Reyting · 30 kun" />
          <Card style={{ paddingVertical: 6 }}>
            {top.length === 0 && <Empty icon="trophy" title="Reyting boʻsh" text="Birinchi boʻling!" />}
            {top.map((r) => (
              <View key={`${r.rank}-${r.name}`} style={[st.lb, r.me && { backgroundColor: C.brandLight, borderRadius: R.sm }]}>
                <Text style={[st.lbRank, r.rank <= 3 && { color: C.gold }]}>{r.rank <= 3 ? ["🥇", "🥈", "🥉"][r.rank - 1] : r.rank}</Text>
                <View style={{ flex: 1 }}>
                  <Text style={T.bold}>{r.name}{r.me ? " (siz)" : ""}</Text>
                  {r.region ? <Text style={T.tiny}>{r.region}</Text> : null}
                </View>
                <Text style={[T.bold, { color: C.brandDark }]}>{r.points}</Text>
              </View>
            ))}
          </Card>

          <Section title="Qanday ball olinadi" />
          <Card style={{ paddingVertical: 4 }}>
            {(w?.rules ?? []).map((r, i, a) => (
              <Row key={r.kind} icon={(RULE_ICON[r.kind] ?? "star") as never} title={r.label}
                subtitle={r.kind === "catch" || r.kind === "report" || r.kind === "bounty" ? "Inspektor tasdiqlagandan keyin" : undefined}
                right={<Text style={[T.bold, { color: "#B45309" }]}>+{r.points}</Text>} last={i === a.length - 1} />
            ))}
          </Card>
          <Text style={T.small}>
            Adolat qoidalari: bitta quti uchun bir marta ball; kuniga {w?.today.cap ?? 150} balldan koʻp emas; soxta kod terib ball yigʻib boʻlmaydi —
            “shubhali quti” ballari faqat inspektor tasdigʻidan keyin beriladi. Ism va telefon soʻralmaydi.
          </Text>

          {w && w.history.length > 0 && (
            <>
              <Section title="Ball tarixi" />
              <Card style={{ paddingVertical: 4 }}>
                {w.history.slice(0, 12).map((h, i, a) => (
                  <Row key={h.id} title={h.note || h.label} subtitle={`${h.label} · ${fmt(h.at)}`}
                    right={<Text style={[T.bold, { color: h.status === "pending" ? C.muted : h.status === "rejected" ? C.danger : h.points < 0 ? C.text : C.ok }]}>
                      {h.status === "pending" ? "⏳ " : h.status === "rejected" ? "✕ " : ""}{h.points > 0 ? "+" : ""}{h.points}
                    </Text>} last={i === a.length - 1} />
                ))}
              </Card>
            </>
          )}
        </View>
      </ScrollView>

      <Modal visible={nickOpen} transparent animationType="slide" onRequestClose={() => setNickOpen(false)}>
        <Pressable style={{ flex: 1, backgroundColor: "rgba(15,27,42,0.4)" }} onPress={() => setNickOpen(false)} />
        <View style={[st.sheet, { paddingBottom: insets.bottom + 20 }]}>
          <Text style={T.h2}>Reytingdagi taxallus</Text>
          <Text style={T.small}>Haqiqiy ism-familiya yozmang. 2–20 belgi.</Text>
          <TextInput value={nick} onChangeText={setNick} autoFocus placeholder="masalan, Hushyor_Aziz" style={u.input} />
          <ErrorNote text={nickErr} />
          <Button title="Saqlash" onPress={saveNick} />
        </View>
      </Modal>
    </View>
  );
}

function Stat({ icon, value, label }: { icon: "flame" | "today" | "hourglass"; value: string; label: string }) {
  return (
    <View style={st.stat}>
      <Ionicons name={icon} size={16} color="#fff" />
      <Text style={st.statVal}>{value}</Text>
      <Text style={st.statLbl}>{label}</Text>
    </View>
  );
}

const st = StyleSheet.create({
  head: { paddingHorizontal: 20, paddingBottom: 22, borderBottomLeftRadius: 32, borderBottomRightRadius: 32, gap: 8 },
  nick: { color: "#fff", fontWeight: "800", fontSize: 17 },
  rank: { flexDirection: "row", gap: 4, alignItems: "center", backgroundColor: "rgba(255,255,255,0.2)", borderRadius: R.pill, paddingHorizontal: 10, paddingVertical: 5 },
  rankText: { color: "#fff", fontWeight: "800" },
  big: { color: "#fff", fontSize: 56, fontWeight: "900", letterSpacing: -2 },
  bigSub: { color: "rgba(255,255,255,0.85)", fontSize: 18, fontWeight: "700", marginBottom: 12 },
  level: { color: "#fff", fontWeight: "700" },
  stats: { flexDirection: "row", gap: 10, marginTop: 8 },
  stat: { flex: 1, backgroundColor: "rgba(255,255,255,0.16)", borderRadius: R.md, padding: 10, alignItems: "center", gap: 2 },
  statVal: { color: "#fff", fontWeight: "900", fontSize: 17 },
  statLbl: { color: "rgba(255,255,255,0.85)", fontSize: 11 },
  badges: { flexDirection: "row", flexWrap: "wrap", gap: 10 },
  badge: { width: "31%", flexGrow: 1, backgroundColor: "#fff", borderRadius: R.md, borderWidth: 1, borderColor: C.border, padding: 10, alignItems: "center", gap: 3 },
  gift: { width: 50, height: 50, borderRadius: 14, backgroundColor: C.goldBg, alignItems: "center", justifyContent: "center" },
  lb: { flexDirection: "row", alignItems: "center", gap: 12, paddingVertical: 10, paddingHorizontal: 6 },
  lbRank: { width: 28, textAlign: "center", fontWeight: "800", color: C.muted, fontSize: 16 },
  sheet: { backgroundColor: "#fff", borderTopLeftRadius: 28, borderTopRightRadius: 28, padding: 20, gap: 12 },
});
