import { Ionicons } from "@expo/vector-icons";
import { Tabs } from "expo-router";
import type { ColorValue } from "react-native";
import { C } from "../../lib/theme";
import type { IconName } from "../../components/ui";

const icon = (name: IconName, active: IconName) => ({ color, focused }: { color: ColorValue; focused: boolean }) =>
  <Ionicons name={focused ? active : name} size={24} color={color as string} />;

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: C.brand,
        tabBarInactiveTintColor: C.faint,
        tabBarStyle: { borderTopColor: C.border, height: 88, paddingTop: 6 },
        tabBarLabelStyle: { fontWeight: "600", fontSize: 11 },
        headerStyle: { backgroundColor: C.bg },
        headerShadowVisible: false,
        headerTitleStyle: { fontWeight: "800", color: C.text, fontSize: 18 },
      }}
    >
      <Tabs.Screen name="index" options={{ title: "Asosiy", headerShown: false, tabBarIcon: icon("home-outline", "home") }} />
      <Tabs.Screen name="xarita" options={{ title: "Xarita", headerShown: false, tabBarIcon: icon("map-outline", "map") }} />
      <Tabs.Screen name="tarix" options={{ title: "Tarix", headerTitle: "Mening tekshiruvlarim", tabBarIcon: icon("time-outline", "time") }} />
      <Tabs.Screen name="ballar" options={{ title: "Ballar", headerShown: false, tabBarIcon: icon("star-outline", "star") }} />
      <Tabs.Screen name="yordamchi" options={{ href: null, title: "Yordamchi", headerTitle: "AI yordamchi" }} />
      <Tabs.Screen name="sozlamalar" options={{ title: "Koʻproq", headerTitle: "Koʻproq", tabBarIcon: icon("grid-outline", "grid") }} />
    </Tabs>
  );
}
