import { Ionicons } from "@expo/vector-icons";
import * as ImagePicker from "expo-image-picker";
import { useEffect, useRef, useState } from "react";
import { Animated, Image, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { api, fmt, KIND_LABEL } from "../lib/api";
import { C, GRAD, R, VERDICT } from "../lib/theme";
import type { AiRisk, BoxInspection, Check, ReportReason, VerifyResponse } from "../lib/types";
import type { PackResult } from "../lib/packnet";
import { checkPackaging } from "../lib/packnetClient";
import { simpleAnswers } from "../lib/answers";
import { Button, Card, ErrorNote, Gradient, IconName, Pill, T, tap, u } from "./ui";

const ANS: Record<string, [string, string, string]> = {
  ha: ["✓ Ha", C.okBg, "#166534"],
  yoq: ["✕ Yoʻq", C.dangerBg, "#991B1B"],
  shubha: ["! Shubhali", C.warnBg, "#92400E"],
  nomalum: ["? Nomaʼlum", "#F1F5F9", C.muted],
};

const CHECK: Record<string, { icon: IconName; fg: string; bg: string }> = {
  ok: { icon: "checkmark", fg: C.ok, bg: C.okBg },
  info: { icon: "information", fg: C.info, bg: C.infoBg },
  warning: { icon: "alert", fg: C.warn, bg: C.warnBg },
  danger: { icon: "close", fg: C.danger, bg: C.dangerBg },
  unknown: { icon: "help", fg: C.muted, bg: "#F1F5F9" },
};

const REASONS: [ReportReason, string][] = [
  ["fake", "Qalbaki deb oʻylayman"], ["reused", "Quti qayta ishlatilgan"], ["no_effect", "Dori taʼsir qilmadi"],
  ["packaging", "Qadoq shubhali"], ["price", "Narx gʻalati"], ["other", "Boshqa"],
];

export function CheckRow({ c }: { c: { status: Check["status"] | "unknown"; title: string; text: string } }) {
  const k = CHECK[c.status] ?? CHECK.unknown;
  return (
    <View style={st.checkRow}>
      <View style={[st.checkIcon, { backgroundColor: k.bg }]}>
        <Ionicons name={k.icon} size={15} color={k.fg} />
      </View>
      <View style={{ flex: 1, gap: 2 }}>
        <Text style={T.bold}>{c.title}</Text>
        <Text style={T.small}>{c.text}</Text>
      </View>
    </View>
  );
}

export function RewardBanner({ r }: { r: VerifyResponse["reward"] }) {
  const scale = useRef(new Animated.Value(0.85)).current;
  useEffect(() => {
    Animated.spring(scale, { toValue: 1, friction: 4, useNativeDriver: true }).start();
  }, [scale]);
  if (!r || (!r.earned && !r.pending && !r.messages.length)) return null;
  return (
    <Animated.View style={{ transform: [{ scale }] }}>
      <Gradient colors={GRAD.gold} style={st.reward}>
        <View style={st.rewardStar}><Ionicons name="star" size={26} color={C.gold} /></View>
        <View style={{ flex: 1 }}>
          <Text style={st.rewardTitle}>
            {r.earned ? `+${r.earned} ball` : r.pending ? `+${r.pending} ball` : "Ballar"}
          </Text>
          <Text style={st.rewardLine}>
            {r.pending && !r.earned ? "Inspektor tasdiqlagach hisobingizga tushadi" : `Jami: ${r.total} ball`}
          </Text>
        </View>
      </Gradient>
    </Animated.View>
  );
}

export function ResultView({ r, onPurchase }: { r: VerifyResponse; onPurchase?: (price: number | null) => Promise<void> }) {
  const v = VERDICT[r.verdict];
  const important = r.checks.filter((c) => c.status === "danger" || c.status === "warning");
  const others = r.checks.filter((c) => c.status !== "danger" && c.status !== "warning");
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    tap(r.verdict === "ok" ? "success" : r.verdict === "danger" ? "error" : "warning");
  }, [r]);

  return (
    <View style={{ gap: 14 }}>
      <Gradient colors={GRAD[r.verdict]} style={st.hero}>
        <View style={st.heroIcon}>
          <Ionicons name={v.ion as IconName} size={40} color="#fff" />
        </View>
        <View style={{ flex: 1, gap: 4 }}>
          <View style={st.heroChip}><Text style={st.heroChipText}>{v.label.toUpperCase()}</Text></View>
          <Text style={st.heroTitle}>{r.headline}</Text>
          {r.drug && <Text style={st.heroSub}>{r.drug.trade_name} {r.drug.strength} · {r.drug.manufacturer.name}</Text>}
        </View>
      </Gradient>

      <RewardBanner r={r.reward} />

      <Card style={{ paddingVertical: 6 }}>
        {simpleAnswers(r.checks, r.ledger?.block?.kind === "purchase" || r.ledger?.block?.kind === "disputed" ? "after" : "before").map((x, i, arr) => (
          <View key={x.q} style={[st.ansRow, i < arr.length - 1 && st.ansBorder]}>
            <View style={{ flex: 1 }}>
              <Text style={T.bold}>{x.q}</Text>
              <Text style={T.small} numberOfLines={2}>{x.note}</Text>
            </View>
            <View style={[st.ansPill, { backgroundColor: ANS[x.a][1] }]}>
              <Text style={{ color: ANS[x.a][2], fontWeight: "800", fontSize: 13 }}>{ANS[x.a][0]}</Text>
            </View>
          </View>
        ))}
      </Card>

      {r.ai_risk && <AiRiskCard risk={r.ai_risk} />}

      <Card>
        <Text style={T.body}>{r.explanation}</Text>
        {r.advice.map((a) => (
          <View key={a} style={{ flexDirection: "row", gap: 8, marginTop: 4 }}>
            <Ionicons name="arrow-forward-circle" size={18} color={C.brand} />
            <Text style={[T.bold, { flex: 1 }]}>{a}</Text>
          </View>
        ))}
        {r.dispense && (
          <View style={[st.note, r.dispense.category === "controlled" && { backgroundColor: C.violetBg }]}>
            <Text style={T.small}><Text style={{ fontWeight: "700", color: C.text }}>{r.dispense.label}. </Text>{r.dispense.note}</Text>
          </View>
        )}
        {r.source !== "asl_belgisi" && (
          <Text style={[T.tiny, { marginTop: 6 }]}>Demo: namuna maʼlumotlar bilan tekshirildi{r.ai_used ? " · tushuntirishni AI yozdi" : ""}</Text>
        )}
      </Card>

      {important.map((c) => (
        <Card key={c.key} tone={c.status === "danger" ? "danger" : undefined} style={c.status === "warning" ? { backgroundColor: C.warnBg, borderColor: "#FDE68A" } : undefined}>
          <CheckRow c={c} />
        </Card>
      ))}

      {onPurchase && r.scan_id && r.verdict !== "danger" && <PurchaseCard onPurchase={onPurchase} />}

      {r.chain.length > 0 && (
        <Card>
          <Text style={T.h3}>Quti qayerdan kelgan</Text>
          <Text style={T.small}>Holati: {r.pack?.status_label}</Text>
          <View style={{ marginTop: 8 }}>
            {r.chain.map((e, i) => {
              const color = e.type === "sold" ? C.danger : e.type === "customs_cleared" ? C.violet : C.brand;
              return (
                <View key={i} style={st.tlRow}>
                  <View style={{ alignItems: "center", width: 18 }}>
                    <View style={[st.tlDot, { backgroundColor: color }]} />
                    {i < r.chain.length - 1 && <View style={st.tlLine} />}
                  </View>
                  <View style={{ flex: 1, paddingBottom: 12 }}>
                    <Text style={T.bold}>{e.label}</Text>
                    <Text style={T.small}>{e.participant}{e.region ? `, ${e.region}` : ""}</Text>
                    <Text style={T.tiny}>{fmt(e.at)}{e.document ? ` · ${e.document}` : ""}</Text>
                  </View>
                </View>
              );
            })}
          </View>
        </Card>
      )}

      {r.ledger && r.ledger.history.length > 0 && (
        <Card>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
            <Ionicons name="link" size={18} color={C.brand} />
            <Text style={T.h3}>Bu qutini kimlar tekshirgan</Text>
          </View>
          <Text style={T.small}>Har bir tekshiruv saqlanadi va oʻchirib boʻlmaydi</Text>
          {r.ledger.history.map((b) => {
            const me = r.ledger?.block?.index === b.index;
            return (
              <View key={b.index} style={[st.block, me && { borderColor: C.brand, backgroundColor: C.brandLight }]}>
                <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
                  <Text style={[T.bold, b.kind === "purchase" && { color: C.danger }]}>{KIND_LABEL[b.kind] ?? b.kind}{me ? " · siz" : ""}</Text>
                  <Text style={T.tiny}>#{b.index}</Text>
                </View>
                <Text style={T.small}>{fmt(b.created_at)} · {[b.pharmacy, b.region].filter(Boolean).join(", ") || "joy koʻrsatilmagan"}</Text>
              </View>
            );
          })}
        </Card>
      )}

      {r.parsed.gtin && <BoxCard r={r} />}

      {others.length > 0 && (
        <Card>
          <Pressable onPress={() => setShowAll(!showAll)} style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
            <Text style={T.h3}>Batafsil maʼlumot ({others.length})</Text>
            <Ionicons name={showAll ? "chevron-up" : "chevron-down"} size={20} color={C.muted} />
          </Pressable>
          {showAll && others.map((c) => <CheckRow key={c.key} c={c} />)}
        </Card>
      )}

      {r.scan_id && <ReportCard r={r} />}
    </View>
  );
}

function PurchaseCard({ onPurchase }: { onPurchase: (price: number | null) => Promise<void> }) {
  const [price, setPrice] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <Card tone="brand">
      <View style={{ flexDirection: "row", gap: 10, alignItems: "center" }}>
        <Ionicons name="bag-check" size={22} color={C.brand} />
        <Text style={[T.h3, { flex: 1 }]}>Sotib oldingizmi?</Text>
        <Pill text="+20 ball" icon="star" color="#B45309" bg={C.goldBg} />
      </View>
      <Text style={T.small}>Quti sizniki deb belgilanadi: kimdir uni qayta sotsa, xaridor ogohlantiriladi.</Text>
      <TextInput value={price} onChangeText={(t) => setPrice(t.replace(/\D/g, ""))} keyboardType="number-pad"
        placeholder="Toʻlagan narx, soʻm (ixtiyoriy)" style={[u.input, { marginTop: 6 }]} />
      <Text style={T.tiny}>Narx juda arzon boʻlsa, tizim ogohlantiradi — bu qalbaki dorining belgilaridan biri.</Text>
      <Button title="Sotib oldim" icon="link" busy={busy} style={{ marginTop: 6 }}
        onPress={async () => { setBusy(true); try { await onPurchase(price ? Number(price) : null); } finally { setBusy(false); } }} />
    </Card>
  );
}

const RISK: Record<AiRisk["level"], { label: string; fg: string; bg: string }> = {
  past: { label: "Past xavf", fg: "#166534", bg: C.okBg },
  "oʻrta": { label: "Oʻrtacha xavf", fg: "#92400E", bg: C.warnBg },
  yuqori: { label: "Yuqori xavf", fg: "#991B1B", bg: C.dangerBg },
};

/** Oʻz modelimiz bahosi — qoʻshimcha signal, asosiy xulosa yuqorida. */
function AiRiskCard({ risk }: { risk: AiRisk }) {
  const l = RISK[risk.level] ?? RISK.past;
  return (
    <Card>
      <View style={{ flexDirection: "row", gap: 10, alignItems: "center" }}>
        <View style={[st.checkIcon, { width: 36, height: 36, borderRadius: 12, backgroundColor: C.violetBg }]}>
          <Ionicons name="analytics" size={18} color={C.violet} />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={T.h3}>AI bahosi</Text>
          <Text style={T.tiny}>Minglab tekshiruvlardan oʻrgangan modelimiz</Text>
        </View>
        <Pill text={l.label} color={l.fg} bg={l.bg} />
      </View>
      <View style={{ height: 8, borderRadius: 4, backgroundColor: "#EEF2F6", overflow: "hidden", marginTop: 4 }}>
        <View style={{ width: `${Math.max(3, risk.score)}%`, height: 8, borderRadius: 4, backgroundColor: l.fg }} />
      </View>
      {risk.level !== "past" && risk.reasons.map((x) => <Text key={x.text} style={T.small}>• {x.text}</Text>)}
      <Text style={T.tiny}>Qoʻshimcha signal. Asosiy xulosa yuqorida.</Text>
    </Card>
  );
}

const PACK_STATUS: Record<PackResult["verdict"], "ok" | "warning" | "unknown"> = {
  asl: "ok", farq: "warning", boshqa: "warning", tanilmadi: "unknown",
};

function BoxCard({ r }: { r: VerifyResponse }) {
  const [local, setLocal] = useState<PackResult | null>(null);
  const [box, setBox] = useState<BoxInspection | null>(null);
  const [photo, setPhoto] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  async function inspect() {
    setErr("");
    const perm = await ImagePicker.requestCameraPermissionsAsync();
    if (!perm.granted) return setErr("Kameraga ruxsat berilmadi.");
    const shot = await ImagePicker.launchCameraAsync({ quality: 0.8 });
    const a = shot.canceled ? null : shot.assets[0];
    if (!a) return;
    setBusy(true);
    setLocal(null);
    setBox(null);
    setPhoto(a.uri);
    let onDevice: PackResult | null = null;
    try {
      // 1. Telefondagi AI — internetsiz, darhol
      onDevice = await checkPackaging(a.uri, a.width, a.height, r.parsed.gtin);
      setLocal(onDevice);
      tap(onDevice.verdict === "asl" ? "success" : onDevice.verdict === "tanilmadi" ? "light" : "warning");
    } catch {
      /* server bilan davom etamiz */
    }
    try {
      // 2. Server: qutidagi yozuvlarni oʻqish (Claude ulangan boʻlsa)
      const res = await api.inspectBox(a.uri, r.parsed.gtin, r.parsed.serial);
      if (res.ai_used) setBox(res);
      else if (!onDevice && res.model) setLocal(res.model);
    } catch (e) {
      if (!onDevice) setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const extra = box?.checks.filter((c) => c.key !== "packnet") ?? [];
  return (
    <Card tone="violet">
      <View style={{ flexDirection: "row", gap: 10, alignItems: "center" }}>
        <Ionicons name="scan-circle" size={22} color={C.violet} />
        <Text style={[T.h3, { flex: 1 }]}>Qutini suratdan tekshirish</Text>
      </View>
      <Text style={T.small}>AI qadoqni asl dizayn bilan solishtiradi. Telefoningizda ishlaydi.</Text>
      <Button title={busy ? "Tekshirilmoqda…" : local ? "Yana suratga olish" : "Qutini suratga olish"} icon="camera" kind="dark"
        busy={busy} onPress={inspect} style={{ marginTop: 6, backgroundColor: C.violet }} />
      <ErrorNote text={err} />
      {local && (
        <View style={{ flexDirection: "row", gap: 10, marginTop: 6 }}>
          {photo && <Image source={{ uri: photo }} style={{ width: 64, height: 64, borderRadius: 10 }} />}
          <View style={{ flex: 1 }}>
            <CheckRow c={{ status: PACK_STATUS[local.verdict], title: local.title, text: local.text }} />
            <Text style={T.tiny}>{local.on_device ? `Telefonda tekshirildi${local.ms ? ` · ${local.ms} ms` : ""} · surat yuborilmadi` : "Serverda tekshirildi"}</Text>
          </View>
        </View>
      )}
      {extra.map((c, i) => <CheckRow key={i} c={c} />)}
    </Card>
  );
}

function ReportCard({ r }: { r: VerifyResponse }) {
  const [open, setOpen] = useState(r.verdict !== "ok");
  const [reason, setReason] = useState<ReportReason>(r.verdict === "ok" ? "no_effect" : "fake");
  const [note, setNote] = useState("");
  const [done, setDone] = useState("");
  const [busy, setBusy] = useState(false);
  async function send() {
    if (!r.scan_id) return;
    setBusy(true);
    try {
      const res = await api.report(r.scan_id, note, reason);
      setDone(res.message);
      tap("success");
    } catch (e) {
      setDone((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  if (!open)
    return (
      <Pressable onPress={() => setOpen(true)} style={{ alignItems: "center", padding: 8 }}>
        <Text style={{ color: C.muted }}>Muammo bormi? <Text style={{ color: C.danger, fontWeight: "700" }}>Xabar bering</Text></Text>
      </Pressable>
    );
  return (
    <Card tone="danger">
      <View style={{ flexDirection: "row", gap: 10, alignItems: "center" }}>
        <Ionicons name="megaphone" size={20} color={C.danger} />
        <Text style={[T.h3, { flex: 1, color: "#7F1D1D" }]}>Inspektorga xabar berish</Text>
      </View>
      <Text style={T.small}>Anonim: ism va telefon soʻralmaydi. Tasdiqlansa +20 ball va +100 mukofot ball.</Text>
      {done ? (
        <View style={{ flexDirection: "row", gap: 8, marginTop: 6 }}>
          <Ionicons name="checkmark-circle" size={20} color={C.ok} />
          <Text style={[T.bold, { flex: 1 }]}>{done}</Text>
        </View>
      ) : (
        <>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 6 }}>
            {REASONS.map(([k, label]) => (
              <Pressable key={k} onPress={() => { tap(); setReason(k); }}
                style={[st.chip, reason === k && { backgroundColor: C.danger, borderColor: C.danger }]}>
                <Text style={{ color: reason === k ? "#fff" : C.text, fontWeight: "600", fontSize: 13 }}>{label}</Text>
              </Pressable>
            ))}
          </View>
          <TextInput value={note} onChangeText={setNote} placeholder="Izoh (ixtiyoriy)" style={[u.input, { marginTop: 6 }]} />
          <Button title="Xabar yuborish" icon="send" kind="danger" busy={busy} onPress={send} style={{ marginTop: 6 }} />
        </>
      )}
    </Card>
  );
}

// Eski ekranlar bilan moslik uchun
export const s = StyleSheet.create({
  card: u.card,
  h: T.h3,
  bold: T.bold,
  body: T.body,
  small: T.small,
  hash: T.mono,
  primary: { backgroundColor: C.brand, borderRadius: R.md, paddingVertical: 14, alignItems: "center" },
  primaryText: { color: "#fff", fontWeight: "700", fontSize: 16 },
  input: { ...u.input, marginVertical: 8 },
});

const st = StyleSheet.create({
  hero: { borderRadius: R.xl, padding: 20, flexDirection: "row", gap: 14, alignItems: "center" },
  heroIcon: { width: 64, height: 64, borderRadius: 32, backgroundColor: "rgba(255,255,255,0.22)", alignItems: "center", justifyContent: "center" },
  heroChip: { alignSelf: "flex-start", backgroundColor: "rgba(255,255,255,0.25)", borderRadius: R.pill, paddingHorizontal: 10, paddingVertical: 3 },
  heroChipText: { color: "#fff", fontWeight: "800", fontSize: 11, letterSpacing: 1 },
  heroTitle: { color: "#fff", fontSize: 21, fontWeight: "800", letterSpacing: -0.3 },
  heroSub: { color: "#fff", opacity: 0.9 },
  reward: { borderRadius: R.lg, padding: 14, flexDirection: "row", gap: 12, alignItems: "center" },
  rewardStar: { width: 46, height: 46, borderRadius: 23, backgroundColor: "#fff", alignItems: "center", justifyContent: "center" },
  rewardTitle: { color: "#fff", fontSize: 20, fontWeight: "900" },
  rewardLine: { color: "#fff", fontSize: 13, fontWeight: "600" },
  note: { marginTop: 8, padding: 10, borderRadius: R.sm, backgroundColor: "#F8FAFC" },
  checkRow: { flexDirection: "row", gap: 12, paddingVertical: 6 },
  ansRow: { flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 11 },
  ansBorder: { borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: C.border },
  ansPill: { borderRadius: 999, paddingHorizontal: 11, paddingVertical: 5 },
  checkIcon: { width: 26, height: 26, borderRadius: 13, alignItems: "center", justifyContent: "center", marginTop: 1 },
  tlRow: { flexDirection: "row", gap: 10 },
  tlDot: { width: 12, height: 12, borderRadius: 6, marginTop: 4 },
  tlLine: { width: 2, flex: 1, backgroundColor: C.border, marginVertical: 2 },
  block: { borderWidth: 1, borderColor: C.border, borderRadius: R.sm, padding: 10, marginTop: 6, gap: 2 },
  chip: { borderWidth: 1, borderColor: C.border, backgroundColor: "#fff", borderRadius: R.pill, paddingHorizontal: 12, paddingVertical: 7 },
});
