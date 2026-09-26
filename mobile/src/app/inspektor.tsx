import { useEffect, useRef, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { s as rs } from "../components/ResultView";
import { api, fmt, TOOL_LABEL } from "../lib/api";
import { getStaff, setStaff } from "../lib/store";
import { C } from "../lib/theme";
import type { Alert, BatchSignal, ChatMessage, PharmacyRisk, StaffSession } from "../lib/types";

type Tab = "signal" | "xavf" | "copilot";
const LEVEL: Record<string, [string, string]> = { yuqori: ["🔴 Yuqori", C.danger], "oʻrta": ["🟠 Oʻrta", C.warn], past: ["🟢 Past", C.ok] };

export default function Inspector() {
  const [staff, setS] = useState<StaffSession | null | undefined>(undefined);
  useEffect(() => { getStaff().then(setS); }, []);
  if (staff === undefined) return null;
  if (!staff) return <Login onDone={setS} />;
  return <Panel staff={staff} onLogout={async () => { await setStaff(null); setS(null); }} />;
}

function Login({ onDone }: { onDone: (s: StaffSession) => void }) {
  const [u, setU] = useState("");
  const [p, setP] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(user = u, pass = p) {
    setBusy(true);
    setErr("");
    try {
      const s = await api.login(user.trim().toLowerCase(), pass);
      if (s.role !== "inspector" && s.role !== "admin") throw new Error("Mobil panel faqat inspektorlar uchun");
      await setStaff(s);
      onDone(s);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <ScrollView style={{ flex: 1, backgroundColor: C.bg }} contentContainerStyle={{ padding: 16, gap: 10 }}>
      <Text style={rs.h}>Farmatsevtika inspektori uchun kirish</Text>
      <Text style={rs.body}>Xaridorlar xabarlari, xavfli dorixonalar va AI copilot. Xaridorlar uchun kirish shart emas.</Text>
      <TextInput value={u} onChangeText={setU} placeholder="Login" autoCapitalize="none" style={rs.input} />
      <TextInput value={p} onChangeText={setP} placeholder="Parol" secureTextEntry style={[rs.input, { marginTop: 0 }]} />
      {err ? <Text style={{ color: C.danger }}>{err}</Text> : null}
      <Pressable style={rs.primary} onPress={() => submit()} disabled={busy}>
        {busy ? <ActivityIndicator color="#fff" /> : <Text style={rs.primaryText}>Kirish</Text>}
      </Pressable>
      <Pressable onPress={() => submit("inspektor", "inspektor123")}>
        <Text style={{ color: C.brand, textAlign: "center", marginTop: 6 }}>Demo: inspektor / inspektor123</Text>
      </Pressable>
    </ScrollView>
  );
}

function Panel({ staff, onLogout }: { staff: StaffSession; onLogout: () => void }) {
  const [tab, setTab] = useState<Tab>("signal");
  return (
    <View style={{ flex: 1, backgroundColor: C.bg }}>
      <View style={{ padding: 12, paddingBottom: 0, gap: 8 }}>
        <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
          <Text style={rs.bold}>{staff.display_name} · {staff.role_label}</Text>
          <Pressable onPress={onLogout}><Text style={{ color: C.danger }}>Chiqish</Text></Pressable>
        </View>
        <View style={st.segment}>
          {([["signal", "Signallar"], ["xavf", "Dorixonalar"], ["copilot", "AI copilot"]] as [Tab, string][]).map(([k, t]) => (
            <Pressable key={k} onPress={() => setTab(k)} style={[st.segBtn, tab === k && st.segActive]}>
              <Text style={[st.segText, tab === k && { color: C.text }]}>{t}</Text>
            </Pressable>
          ))}
        </View>
      </View>
      {tab === "signal" ? <Alerts /> : tab === "xavf" ? <Risks /> : <Copilot />}
    </View>
  );
}

function Alerts() {
  const [rows, setRows] = useState<Alert[] | null>(null);
  const [batches, setBatches] = useState<BatchSignal[]>([]);
  const [err, setErr] = useState("");
  const load = () => {
    api.alerts().then(setRows).catch((e) => setErr(e.message));
    api.batchSignals().then(setBatches).catch(() => {});
  };
  useEffect(load, []);
  async function resolve(id: number, ok: boolean) {
    await api.resolveReport(id, ok).catch((e) => setErr(e.message));
    load();
  }
  return (
    <ScrollView contentContainerStyle={{ padding: 12, gap: 8, paddingBottom: 40 }}>
      <Text style={rs.small}>Isbot emas — tekshiruv uchun signal. Hech kim aybdor deb eʼlon qilinmaydi.</Text>
      {batches.filter((b) => b.level !== "past").map((b) => (
        <View key={`${b.drug}-${b.batch}`} style={[rs.card, { borderColor: "#FDE68A", backgroundColor: C.warnBg }]}>
          <Text style={rs.bold}>🧪 Partiya signali: {b.drug} · {b.batch}</Text>
          <Text style={rs.small}>{b.reports} ta shikoyat ({b.quality_reports} ta “taʼsir qilmadi”/qadoq){b.regions.length ? ` · ${b.regions.join(", ")}` : ""}</Text>
          <Text style={rs.small}>{b.note}</Text>
        </View>
      ))}
      {!rows && !err && <ActivityIndicator color={C.brand} />}
      {err ? <Text style={{ color: C.danger }}>{err}</Text> : null}
      {rows?.map((a) => (
        <View key={a.scan_id} style={[rs.card, a.reported && { borderColor: "#fecaca" }]}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
            <Text style={[rs.bold, { flex: 1, color: a.verdict === "danger" ? C.danger : a.verdict === "warning" ? C.warn : C.violet }]}>
              {a.verdict === "danger" ? "✕" : a.verdict === "warning" ? "!" : "◆"} {a.drug} · SN {a.serial}
            </Text>
            {a.ml_score != null && (
              <View style={{ paddingHorizontal: 8, paddingVertical: 2, borderRadius: 999,
                backgroundColor: a.ml_score >= 50 ? C.dangerBg : a.ml_score >= 20 ? C.warnBg : "#F1F5F9" }}>
                <Text style={{ fontSize: 12, fontWeight: "800", color: a.ml_score >= 50 ? C.danger : a.ml_score >= 20 ? C.warn : C.muted }}>AI {a.ml_score}</Text>
              </View>
            )}
          </View>
          <Text style={rs.body}>{a.reasons.join(", ") || "Qoidalar muammo topmadi, AI modeli shubha qildi"}</Text>
          <Text style={rs.small}>{[a.pharmacy || "dorixona nomaʼlum", a.region, fmt(a.at)].filter(Boolean).join(" · ")}</Text>
          {a.reported && <Text style={{ color: C.danger, fontSize: 12 }}>📣 Xaridor xabar berdi{a.report_reason ? ` (${a.report_reason})` : ""}{a.report_note ? `: ${a.report_note}` : ""}</Text>}
          {a.report_status === "tasdiqlandi" && <Text style={{ color: C.ok, fontSize: 12, fontWeight: "700" }}>✓ Tasdiqlandi — xaridorga ball berildi</Text>}
          {a.report_status === "rad_etildi" && <Text style={rs.small}>Rad etildi</Text>}
          {(a.verdict === "danger" || a.reported || (a.ml_score ?? 0) >= 50) && !["tasdiqlandi", "rad_etildi"].includes(a.report_status) && (
            <View style={{ flexDirection: "row", gap: 8, marginTop: 6 }}>
              <Pressable onPress={() => resolve(a.scan_id, true)} style={[st.small, { backgroundColor: C.ok }]}><Text style={st.smallText}>Tasdiqlash</Text></Pressable>
              <Pressable onPress={() => resolve(a.scan_id, false)} style={[st.small, { backgroundColor: C.muted }]}><Text style={st.smallText}>Rad etish</Text></Pressable>
            </View>
          )}
        </View>
      ))}
    </ScrollView>
  );
}

function Risks() {
  const [rows, setRows] = useState<PharmacyRisk[] | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => { api.risks().then(setRows).catch((e) => setErr(e.message)); }, []);
  return (
    <ScrollView contentContainerStyle={{ padding: 12, gap: 8, paddingBottom: 40 }}>
      {!rows && !err && <ActivityIndicator color={C.brand} />}
      {err ? <Text style={{ color: C.danger }}>{err}</Text> : null}
      {rows?.map((r) => {
        const [lbl, color] = LEVEL[r.level] ?? [r.level, C.muted];
        return (
          <View key={r.pharmacy.id} style={rs.card}>
            <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
              <Text style={[rs.bold, { flex: 1 }]}>{r.pharmacy.name}</Text>
              <Text style={{ color, fontWeight: "700" }}>{lbl}</Text>
            </View>
            <Text style={rs.small}>{r.pharmacy.region} · qabul {r.received} · sotuv {r.sold} · skaner {r.scans}{r.ml_outlier ? " · ML: gʻayrioddiy" : ""}</Text>
            {r.signals.map((s) => <Text key={s} style={rs.body}>• {s}</Text>)}
          </View>
        );
      })}
    </ScrollView>
  );
}

type Turn = ChatMessage & { tools?: string };
const Q = ["Qaysi dorixonani birinchi tekshiray va nima uchun?", "Qayta ishlatilgan quti signallari qayerda koʻp?", "Kulrang import boʻyicha nima bor?"];

function Copilot() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scroll = useRef<ScrollView>(null);
  async function ask(text: string) {
    if (!text.trim() || busy) return;
    const next: Turn[] = [...turns, { role: "user", content: text.trim() }];
    setTurns(next);
    setInput("");
    setBusy(true);
    try {
      const r = await api.inspectorChat(next.map(({ role, content }) => ({ role, content })));
      setTurns([...next, { role: "assistant", content: r.answer, tools: r.steps.map((s) => TOOL_LABEL[s.tool] ?? s.tool).join(" → ") }]);
    } catch (e) {
      setTurns([...next, { role: "assistant", content: `Xato: ${(e as Error).message}` }]);
    } finally {
      setBusy(false);
      setTimeout(() => scroll.current?.scrollToEnd({ animated: true }), 100);
    }
  }
  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined} keyboardVerticalOffset={100}>
      <ScrollView ref={scroll} contentContainerStyle={{ padding: 12, gap: 8 }}>
        {turns.length === 0 && Q.map((q) => (
          <Pressable key={q} onPress={() => ask(q)} style={st.chip}><Text>{q}</Text></Pressable>
        ))}
        {turns.map((t, i) => (
          <View key={i} style={t.role === "user" ? st.user : st.bot}>
            <Text style={t.role === "user" ? { color: "#fff" } : rs.body}>{t.content}</Text>
            {t.tools ? <Text style={[rs.small, { marginTop: 4 }]}>🤖 {t.tools}</Text> : null}
          </View>
        ))}
        {busy && <ActivityIndicator color={C.brand} style={{ alignSelf: "flex-start" }} />}
      </ScrollView>
      <View style={st.inputRow}>
        <TextInput value={input} onChangeText={setInput} placeholder="Savol…" style={[rs.input, { flex: 1, marginVertical: 0 }]} onSubmitEditing={() => ask(input)} />
        <Pressable style={[rs.primary, { paddingHorizontal: 18 }]} onPress={() => ask(input)}><Text style={rs.primaryText}>➤</Text></Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

const st = StyleSheet.create({
  small: { paddingHorizontal: 12, paddingVertical: 7, borderRadius: 10 },
  smallText: { color: "#fff", fontWeight: "700", fontSize: 13 },
  segment: { flexDirection: "row", backgroundColor: "#e5e7eb", borderRadius: 12, padding: 4 },
  segBtn: { flex: 1, paddingVertical: 8, borderRadius: 9, alignItems: "center" },
  segActive: { backgroundColor: "#fff" },
  segText: { fontWeight: "600", color: C.muted },
  chip: { backgroundColor: "#fff", borderRadius: 20, borderWidth: 1, borderColor: C.border, paddingVertical: 8, paddingHorizontal: 14, alignSelf: "flex-start" },
  user: { alignSelf: "flex-end", backgroundColor: C.brand, borderRadius: 16, padding: 12, maxWidth: "85%" },
  bot: { backgroundColor: "#fff", borderRadius: 16, padding: 12, borderWidth: 1, borderColor: C.border, maxWidth: "92%" },
  inputRow: { flexDirection: "row", gap: 8, padding: 12, borderTopWidth: 1, borderTopColor: C.border, backgroundColor: "#fff" },
});
