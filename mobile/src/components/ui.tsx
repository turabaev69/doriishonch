import { Ionicons } from "@expo/vector-icons";
import * as Haptics from "expo-haptics";
import { LinearGradient } from "expo-linear-gradient";
import { ComponentProps, ReactNode } from "react";
import { ActivityIndicator, Platform, Pressable, ScrollView, StyleProp, StyleSheet, Text, TextStyle, View, ViewStyle } from "react-native";
import { C, GRAD, R, shadow } from "../lib/theme";

export type IconName = ComponentProps<typeof Ionicons>["name"];

export function tap(kind: "light" | "success" | "warning" | "error" = "light") {
  if (Platform.OS === "web") return;
  if (kind === "light") Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
  else Haptics.notificationAsync(
    kind === "success" ? Haptics.NotificationFeedbackType.Success
      : kind === "warning" ? Haptics.NotificationFeedbackType.Warning : Haptics.NotificationFeedbackType.Error,
  ).catch(() => {});
}

export function Screen({ children, scroll = true, pad = true, refreshControl }: {
  children: ReactNode; scroll?: boolean; pad?: boolean; refreshControl?: ComponentProps<typeof ScrollView>["refreshControl"];
}) {
  if (!scroll) return <View style={{ flex: 1, backgroundColor: C.bg }}>{children}</View>;
  return (
    <ScrollView style={{ flex: 1, backgroundColor: C.bg }} refreshControl={refreshControl}
      contentContainerStyle={[{ paddingBottom: 48, gap: 14 }, pad && { padding: 16 }]} keyboardShouldPersistTaps="handled">
      {children}
    </ScrollView>
  );
}

export function Card({ children, style, onPress, tone }: {
  children: ReactNode; style?: StyleProp<ViewStyle>; onPress?: () => void; tone?: "brand" | "gold" | "danger" | "violet";
}) {
  const toneStyle = tone === "brand" ? { backgroundColor: C.brandLight, borderColor: "#C7EDE3" }
    : tone === "gold" ? { backgroundColor: C.goldBg, borderColor: "#FCE3A6" }
    : tone === "danger" ? { backgroundColor: C.dangerBg, borderColor: "#FECACA" }
    : tone === "violet" ? { backgroundColor: C.violetBg, borderColor: "#DDD6FE" } : null;
  const body = <View style={[u.card, toneStyle, style]}>{children}</View>;
  if (!onPress) return body;
  return (
    <Pressable onPress={() => { tap(); onPress(); }} style={({ pressed }) => pressed && { opacity: 0.85, transform: [{ scale: 0.99 }] }}>
      {body}
    </Pressable>
  );
}

type BtnKind = "primary" | "secondary" | "ghost" | "danger" | "dark" | "gold" | "white";

export function Button({ title, onPress, icon, kind = "primary", busy, disabled, style, size = "md" }: {
  title: string; onPress: () => void; icon?: IconName; kind?: BtnKind; busy?: boolean; disabled?: boolean;
  style?: StyleProp<ViewStyle>; size?: "md" | "lg" | "sm";
}) {
  const bg: Record<BtnKind, string> = { primary: C.brand, secondary: "#fff", ghost: "transparent", danger: C.danger, dark: C.text, gold: C.gold, white: "#fff" };
  const fg: Record<BtnKind, string> = { primary: "#fff", secondary: C.text, ghost: C.brand, danger: "#fff", dark: "#fff", gold: "#fff", white: C.brandDark };
  const pad = size === "lg" ? 18 : size === "sm" ? 9 : 14;
  return (
    <Pressable
      disabled={disabled || busy}
      onPress={() => { tap(); onPress(); }}
      style={({ pressed }) => [
        u.btn, { backgroundColor: bg[kind], paddingVertical: pad },
        kind === "secondary" && { borderWidth: 1, borderColor: C.border },
        (kind === "primary" || kind === "white") && shadow,
        (disabled || busy) && { opacity: 0.55 }, pressed && { opacity: 0.85, transform: [{ scale: 0.985 }] }, style,
      ]}
    >
      {busy ? <ActivityIndicator color={fg[kind]} /> : (
        <>
          {icon && <Ionicons name={icon} size={size === "lg" ? 22 : 18} color={fg[kind]} />}
          <Text style={[u.btnText, { color: fg[kind], fontSize: size === "lg" ? 18 : size === "sm" ? 14 : 16 }]}>{title}</Text>
        </>
      )}
    </Pressable>
  );
}

export function Gradient({ colors = GRAD.brand, style, children }: { colors?: readonly [string, string]; style?: StyleProp<ViewStyle>; children: ReactNode }) {
  return <LinearGradient colors={colors} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={style}>{children}</LinearGradient>;
}

export function IconCircle({ name, color = C.brand, bg = C.brandLight, size = 40 }: { name: IconName; color?: string; bg?: string; size?: number }) {
  return (
    <View style={{ width: size, height: size, borderRadius: size / 2, backgroundColor: bg, alignItems: "center", justifyContent: "center" }}>
      <Ionicons name={name} size={size * 0.52} color={color} />
    </View>
  );
}

export function Row({ icon, iconColor, iconBg, title, subtitle, right, onPress, last }: {
  icon?: IconName; iconColor?: string; iconBg?: string; title: string; subtitle?: string; right?: ReactNode; onPress?: () => void; last?: boolean;
}) {
  const content = (
    <View style={[u.row, !last && u.rowBorder]}>
      {icon && <IconCircle name={icon} color={iconColor} bg={iconBg} size={36} />}
      <View style={{ flex: 1 }}>
        <Text style={T.bold} numberOfLines={2}>{title}</Text>
        {subtitle ? <Text style={T.small} numberOfLines={2}>{subtitle}</Text> : null}
      </View>
      {right ?? (onPress ? <Ionicons name="chevron-forward" size={18} color={C.faint} /> : null)}
    </View>
  );
  return onPress ? <Pressable onPress={() => { tap(); onPress(); }} style={({ pressed }) => pressed && { opacity: 0.6 }}>{content}</Pressable> : content;
}

export function Pill({ text, color = C.brand, bg = C.brandLight, icon }: { text: string; color?: string; bg?: string; icon?: IconName }) {
  return (
    <View style={[u.pill, { backgroundColor: bg }]}>
      {icon && <Ionicons name={icon} size={13} color={color} />}
      <Text style={{ color, fontWeight: "700", fontSize: 12 }}>{text}</Text>
    </View>
  );
}

export function Progress({ value, color = C.gold, track = "rgba(255,255,255,0.3)", height = 8 }: { value: number; color?: string; track?: string; height?: number }) {
  return (
    <View style={{ height, borderRadius: height, backgroundColor: track, overflow: "hidden" }}>
      <View style={{ width: `${Math.max(3, Math.min(100, value * 100))}%`, height, borderRadius: height, backgroundColor: color }} />
    </View>
  );
}

export function Section({ title, action, onAction }: { title: string; action?: string; onAction?: () => void }) {
  return (
    <View style={{ flexDirection: "row", alignItems: "flex-end", justifyContent: "space-between", marginTop: 6 }}>
      <Text style={T.h2}>{title}</Text>
      {action && <Pressable onPress={onAction}><Text style={{ color: C.brand, fontWeight: "700" }}>{action}</Text></Pressable>}
    </View>
  );
}

export function Empty({ icon, title, text, action }: { icon: IconName; title: string; text: string; action?: ReactNode }) {
  return (
    <View style={{ alignItems: "center", padding: 28, gap: 8 }}>
      <IconCircle name={icon} size={64} />
      <Text style={[T.h2, { textAlign: "center" }]}>{title}</Text>
      <Text style={[T.body, { textAlign: "center", color: C.muted }]}>{text}</Text>
      {action}
    </View>
  );
}

export function ErrorNote({ text }: { text: string }) {
  if (!text) return null;
  return (
    <View style={u.error}>
      <Ionicons name="warning" size={18} color={C.danger} />
      <Text style={{ color: "#991B1B", flex: 1 }}>{text}</Text>
    </View>
  );
}

export const T = StyleSheet.create({
  h1: { fontSize: 28, fontWeight: "800", color: C.text, letterSpacing: -0.5 },
  h2: { fontSize: 18, fontWeight: "800", color: C.text, letterSpacing: -0.2 },
  h3: { fontSize: 16, fontWeight: "700", color: C.text },
  bold: { fontSize: 15, fontWeight: "600", color: C.text },
  body: { fontSize: 15, color: C.body, lineHeight: 21 },
  small: { fontSize: 13, color: C.muted, lineHeight: 18 },
  tiny: { fontSize: 11, color: C.faint },
  white: { color: "#fff" },
  mono: { fontFamily: Platform.OS === "ios" ? "Menlo" : "monospace", fontSize: 10, color: C.faint },
});

export const u = StyleSheet.create({
  card: { backgroundColor: C.card, borderRadius: R.lg, borderWidth: 1, borderColor: C.border, padding: 16, gap: 6, ...shadow },
  btn: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, borderRadius: R.md, paddingHorizontal: 18 },
  btnText: { fontWeight: "700" },
  row: { flexDirection: "row", alignItems: "center", gap: 12, paddingVertical: 12 },
  rowBorder: { borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: C.border },
  pill: { flexDirection: "row", alignItems: "center", gap: 4, paddingHorizontal: 10, paddingVertical: 4, borderRadius: R.pill, alignSelf: "flex-start" },
  input: { backgroundColor: "#fff", borderWidth: 1, borderColor: C.border, borderRadius: R.md, paddingHorizontal: 14, paddingVertical: 13, fontSize: 16, color: C.text },
  error: { flexDirection: "row", gap: 8, alignItems: "center", backgroundColor: C.dangerBg, padding: 12, borderRadius: R.md },
  segment: { flexDirection: "row", backgroundColor: "rgba(255,255,255,0.18)", borderRadius: R.pill, padding: 4 },
});
