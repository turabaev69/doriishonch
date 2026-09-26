import AsyncStorage from "@react-native-async-storage/async-storage";
import { useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { Text, TextInput } from "react-native";
import { Button, Card, IconName, Row, Screen, Section, T, u } from "../../components/ui";
import { api, getServer, setServer } from "../../lib/api";
import { C } from "../../lib/theme";

const LINKS: [string, IconName, string, string, string?, string?][] = [
  ["/yordamchi", "chatbubbles", "AI yordamchi", "Dori haqida oddiy tilda savol bering", C.brand, C.brandLight],
  ["/ai", "sparkles", "Bizning AI", "Qadoq modelini internetsiz sinab koʻring", C.violet, C.violetBg],
  ["/dorilar", "search", "Dori qidirish", "Rasmiy maʼlumot va arzonroq oʻxshashlari"],
  ["/demo", "flask", "Demo stsenariylar", "Kodsiz sinab koʻrish: haqiqiy, soxta, qayta sotilgan…", C.gold, C.goldBg],
  ["/zanjir", "list", "Tekshiruvlar jurnali", "Barcha tekshiruvlar oʻchirib boʻlmaydigan jurnalda", C.violet, C.violetBg],
  ["/inspektor", "shield-half", "Inspektor paneli", "Signallar, xavfli dorixonalar, AI copilot (login)", C.danger, C.dangerBg],
];

export default function More() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => { getServer().then(setUrl); }, []);

  async function save() {
    setBusy(true);
    setStatus("");
    try {
      await setServer(url);
      const h = await api.health();
      setStatus(`✓ Ulandi. AI: ${h.ai_enabled ? "yoqilgan" : "kalit yoʻq (soddalashtirilgan rejim)"} · Asl Belgisi: ${h.asl_belgisi ? "ulangan" : "demo"}`);
    } catch (e) {
      setStatus(`✕ ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen>
      <Card style={{ paddingVertical: 4 }}>
        {LINKS.map(([href, icon, title, sub, fg, bg], i) => (
          <Row key={href} icon={icon} iconColor={fg} iconBg={bg} title={title} subtitle={sub} onPress={() => router.push(href as never)} last={i === LINKS.length - 1} />
        ))}
      </Card>

      <Section title="Server" />
      <Card>
        <Text style={T.small}>Kompyuterda ./start.sh public ni ishga tushiring va chiqqan https://….trycloudflare.com manzilini yozing.</Text>
        <TextInput value={url} onChangeText={setUrl} placeholder="https://….trycloudflare.com" autoCapitalize="none"
          autoCorrect={false} keyboardType="url" style={[u.input, { marginTop: 6 }]} />
        <Button title="Saqlash va tekshirish" icon="cloud-done" busy={busy} onPress={save} style={{ marginTop: 6 }} />
        {status ? <Text style={[T.small, { marginTop: 4 }]}>{status}</Text> : null}
      </Card>

      <Section title="Maxfiylik" />
      <Card>
        <Row icon="finger-print" title="Anonim ID" subtitle="Ism, telefon va joylashuv serverda saqlanmaydi. Qurilmada tasodifiy ID — faqat ballar va “shu xaridorning oʻzi” ekanini ajratish uchun." />
        <Row icon="phone-portrait" title="Tarix faqat telefoningizda" subtitle="Tekshiruvlar roʻyxati serverga yuborilmaydi." />
        <Row icon="medkit" iconColor={C.danger} iconBg={C.dangerBg} title="Tibbiy maslahat emas" subtitle="Dori tanlash va almashtirish boʻyicha shifokor yoki farmatsevt bilan maslahatlashing." last />
      </Card>
      <Button title="Tanishtiruvni qayta koʻrish" kind="ghost" icon="play-circle" onPress={async () => {
        await AsyncStorage.removeItem("doriishonch_onboarded").catch(() => {});
        router.push("/onboarding");
      }} />
      <Text style={[T.tiny, { textAlign: "center" }]}>DoriIshonch AI · demo versiya</Text>
    </Screen>
  );
}
