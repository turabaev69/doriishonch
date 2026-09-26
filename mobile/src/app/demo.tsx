import { useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { ActivityIndicator, Text, View } from "react-native";
import { Card, ErrorNote, IconName, Pill, Row, Screen, T } from "../components/ui";
import { api } from "../lib/api";
import { runVerify } from "../lib/scan";
import { setPharmacy } from "../lib/store";
import { VERDICT } from "../lib/theme";
import type { DemoCode } from "../lib/types";

export default function Demo() {
  const router = useRouter();
  const [rows, setRows] = useState<DemoCode[] | null>(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  useEffect(() => { api.demoCodes().then(setRows).catch((e) => setError(e.message)); }, []);

  async function run(d: DemoCode) {
    setBusy(d.key);
    setError("");
    try {
      if (d.pharmacy_id) {
        const all = await api.pharmacies().catch(() => []);
        await setPharmacy(all.find((p) => p.id === d.pharmacy_id) ?? null);
      } else await setPharmacy(null);
      const item = await runVerify(d.code, d.mode);
      router.push({ pathname: "/natija/[id]", params: { id: item.id, fresh: "1" } });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }

  return (
    <Screen>
      <Text style={T.body}>Har bir stsenariy haqiqiy tekshiruvdan oʻtadi: qoidalar, bojxona yozuvi va DoriIshonch zanjiri. Hakamlarga koʻrsatish uchun qulay.</Text>
      <ErrorNote text={error} />
      {!rows && !error && <ActivityIndicator />}
      <Card style={{ paddingVertical: 4 }}>
        {rows?.map((d, i) => {
          const v = VERDICT[(d.expected as keyof typeof VERDICT)] ?? VERDICT.unknown;
          return (
            <Row key={d.key} icon={v.ion as IconName} iconColor={v.bg} iconBg={v.soft} title={d.title}
              subtitle={`${d.trade_name}${d.pharmacy_name ? ` · ${d.pharmacy_name}` : ""}`}
              right={busy === d.key ? <ActivityIndicator /> : d.mode === "after" ? <Pill text="xariddan keyin" /> : undefined}
              onPress={() => run(d)} last={i === rows.length - 1} />
          );
        })}
      </Card>
      <View />
    </Screen>
  );
}
