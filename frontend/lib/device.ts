// Anonim qurilma ID: faqat "shu xaridorning oʻzi qayta skanerlayapti" ni ajratish uchun.
// Ism, telefon yoki joylashuv emas. Brauzer xotirasida saqlanadi; boʻlmasa, sahifa ochiq turgan vaqtda amal qiladi.
let memoryId = "";

export function getDeviceId(): string {
  try {
    let id = localStorage.getItem("doriishonch_device");
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem("doriishonch_device", id);
    }
    return id;
  } catch {
    if (!memoryId) memoryId = Math.random().toString(36).slice(2) + Date.now().toString(36);
    return memoryId;
  }
}
