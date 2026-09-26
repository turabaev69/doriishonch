// DoriIshonch dizayn tizimi: bitta joyda ranglar, radiuslar va soyalar.
export const C = {
  brand: "#0E8C78",
  brandDark: "#0A5E52",
  brandDeep: "#063F37",
  brandLight: "#E7F6F2",
  brand2: "#19B394",
  bg: "#F3F6F8",
  card: "#FFFFFF",
  text: "#0F1B2A",
  body: "#334155",
  muted: "#64748B",
  faint: "#94A3B8",
  border: "#E4E9EF",
  ok: "#16A34A",
  okBg: "#DCFCE7",
  warn: "#D97706",
  warnBg: "#FEF3C7",
  danger: "#DC2626",
  dangerBg: "#FEE2E2",
  info: "#0284C7",
  infoBg: "#E0F2FE",
  gold: "#F59E0B",
  goldBg: "#FFF7E0",
  violet: "#6D5AE6",
  violetBg: "#EEEBFF",
};

export const R = { sm: 10, md: 14, lg: 20, xl: 28, pill: 999 };

export const shadow = {
  shadowColor: "#0F1B2A",
  shadowOpacity: 0.06,
  shadowRadius: 12,
  shadowOffset: { width: 0, height: 4 },
  elevation: 2,
} as const;

export const GRAD = {
  brand: ["#0B7A69", "#13A38A"] as const,
  ok: ["#15803D", "#22C55E"] as const,
  warning: ["#B45309", "#F59E0B"] as const,
  danger: ["#B91C1C", "#EF4444"] as const,
  unknown: ["#475569", "#94A3B8"] as const,
  gold: ["#F59E0B", "#FBBF24"] as const,
  violet: ["#5B47D6", "#8B7CF6"] as const,
};

export const VERDICT = {
  ok: { bg: C.ok, soft: C.okBg, icon: "✓", ion: "shield-checkmark", label: "Xavfsiz" },
  warning: { bg: "#F59E0B", soft: C.warnBg, icon: "!", ion: "alert-circle", label: "Diqqat" },
  danger: { bg: C.danger, soft: C.dangerBg, icon: "✕", ion: "close-circle", label: "Xavfli" },
  unknown: { bg: "#64748B", soft: "#F1F5F9", icon: "?", ion: "help-circle", label: "Nomaʼlum" },
} as const;
