# DoriIshonch — iOS / Android ilova (Expo)

Veb-versiya bilan bir xil backendga ulanadi.

| Boʻlim | Nima qiladi |
|---|---|
| 🏠 Asosiy | Gradient bosh sahifa: katta “Skanerlash” (toʻliq ekranli kamera, chiroq), suratdan, galereya, kodni yozish, dorixona, haftalik missiya, soʻnggi tekshiruvlar |
| ⭐ Ballar | Ball, daraja, ketma-ket kunlar, missiyalar, nishonlar, mukofotlar, reyting, taxallus, ball tarixi |
| 📷 Natija | Kamerada DataMatrix/QR skaner, **suratdan tekshirish** (AI kodni oʻqiydi), qoʻlda kiritish, "Sotib oldim", AI qadoq ekspertizasi, inspektorga xabar |
| 🕘 Tarix | Telefondagi barcha tekshiruvlar, **Mening dorilarim** (sotib olingan qutilar va yaroqlilik muddati: “12 kun qoldi”, “muddati oʻtgan”) |
| 🤖 AI yordamchi | Claude agent: qutini tekshiradi, dori va analog qidiradi, zanjir tarixini va yaqin dorixonalarni koʻradi |
| 💊 Dorilar | Qidiruv (imlo xatolariga chidamli) → Ishonch kartasi (manba havolalari bilan) → analoglar |
| ☰ Koʻproq | Demo stsenariylar (kodsiz sinash), yaqin dorixonalar (Apple Maps), DoriIshonch zanjiri, **inspektor paneli** (signallar, xavfli dorixonalar, AI copilot — login bilan), server manzili |

## iPhone da ishga tushirish (Xcode shart emas)

1. iPhone ga App Store dan **Expo Go** ni oʻrnating.
2. Kompyuterda backend + veb:
   ```bash
   cd ~/Desktop/hackathon
   ./start.sh public        # https://….trycloudflare.com manzilini eslab qoling
   ```
3. Yangi terminalda ilova:
   ```bash
   cd ~/Desktop/hackathon
   ./start.sh mobile        # yoki: cd mobile && npm install && npx expo start
   ```
4. Terminaldagi QR kodni iPhone **Kamera** ilovasi bilan skanerlang → Expo Go da ochiladi
   (telefon va kompyuter bitta Wi-Fi da boʻlishi kerak; boshqa tarmoqda boʻlsa: `npx expo start --tunnel`).
5. Ilovada **Koʻproq** → 2-qadamdagi https manzilni yozing → "Saqlash va tekshirish".
6. Kod yoʻq boʻlsa: **Koʻproq → Demo stsenariylar** — har bir stsenariy haqiqiy tekshiruvdan oʻtadi.

## App Store / TestFlight uchun build

Apple Developer hisobi kerak (yiliga $99). `eas.json` tayyor:
```bash
cd mobile
npx eas-cli@latest login
npx eas-cli@latest build --platform ios --profile preview      # ichki tarqatish (roʻyxatdagi iPhone lar)
npx eas-cli@latest build --platform ios --profile production   # App Store / TestFlight
npx eas-cli@latest submit --platform ios
```
Build uchun `app.json` → `extra.apiUrl` ga doimiy server manzilini yozing (tunnel manzili har safar oʻzgaradi).

## Tuzilma
- `src/app/_layout.tsx` — Stack (tablar + batafsil sahifalar)
- `src/app/(tabs)/` — `index` (skaner), `tarix`, `yordamchi`, `dori` (qidiruv), `sozlamalar` (Koʻproq)
- `src/app/natija/[id].tsx` — saqlangan natija; `dori/[id].tsx` — Ishonch kartasi va analoglar
- `src/app/dorixonalar.tsx`, `demo.tsx`, `zanjir.tsx`, `inspektor.tsx`
- `src/lib/store.ts` — qurilmadagi tarix, tanlangan dorixona, xodim sessiyasi (AsyncStorage)
- `src/components/ResultView.tsx` — natija, qutining yoʻli, zanjir, AI qadoq ekspertizasi, xabar berish
- `src/lib/api.ts` — backend API (server manzili + `/api`)

Tekshiruv: `npm run typecheck`
