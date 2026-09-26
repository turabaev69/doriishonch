import AsyncStorage from "@react-native-async-storage/async-storage";
import * as Crypto from "expo-crypto";

// Anonim qurilma ID: ism yoki telefon raqami emas. Server faqat uning hashini saqlaydi.
let id: string | null = null;

export async function getDeviceId(): Promise<string> {
  if (id) return id;
  id = await AsyncStorage.getItem("doriishonch_device").catch(() => null);
  if (!id) {
    id = Crypto.randomUUID();
    await AsyncStorage.setItem("doriishonch_device", id).catch(() => {});
  }
  return id;
}
