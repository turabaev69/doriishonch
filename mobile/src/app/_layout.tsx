import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { C } from "../lib/theme";

export default function RootLayout() {
  return (
    <>
      <StatusBar style="dark" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: C.bg },
          headerShadowVisible: false,
          headerTitleStyle: { fontWeight: "800", color: C.text },
          headerTintColor: C.brand,
          headerBackTitle: "Orqaga",
          contentStyle: { backgroundColor: C.bg },
        }}
      >
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="skaner" options={{ presentation: "fullScreenModal", headerShown: false, animation: "fade" }} />
        <Stack.Screen name="onboarding" options={{ presentation: "fullScreenModal", headerShown: false }} />
        <Stack.Screen name="natija/[id]" options={{ title: "Natija" }} />
        <Stack.Screen name="dori/[id]" options={{ title: "Dori haqida" }} />
        <Stack.Screen name="dorilar" options={{ title: "Dori qidirish" }} />
        <Stack.Screen name="dorixonalar" options={{ title: "Yaqin dorixonalar" }} />
        <Stack.Screen name="zanjir" options={{ title: "Tekshiruvlar jurnali" }} />
        <Stack.Screen name="demo" options={{ title: "Demo stsenariylar" }} />
        <Stack.Screen name="inspektor" options={{ title: "Inspektor" }} />
        <Stack.Screen name="ai" options={{ title: "Bizning AI" }} />
      </Stack>
    </>
  );
}
