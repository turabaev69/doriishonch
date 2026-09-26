# DoriIshonch veb interfeysi

## Yoʻnalish

Sokin yashil va oq ranglar, oʻqilishi ravshan matn, yagona ikonka uslubi va birlamchi
“Qutini tekshirish” amali. Maqsad — yoshidan qatʼi nazar foydalanishni osonlashtirish.
7–70 yosh oraligʻidagi haqiqiy foydalanuvchilar bilan usability sinovi hali oʻtkazilmagan.

- Manrope variable shrift lokal yuklanadi: tashqi font servisi talab qilinmaydi.
  Litsenziya: `public/fonts/OFL.txt`.
- `AppHeader`: faol sahifa belgisi, mobil pastki navigatsiya, klaviatura bilan ishlaydigan menyu.
- “Katta matn” sozlamasi brauzerda saqlanadi. Oddiy brauzer zoom ham cheklanmagan.
- Asosiy boshqaruvlar kamida 44 px balandlikda; fokus belgisi va asosiy qismga oʻtish havolasi bor.
- `prefers-reduced-motion` qoʻllanadi. Natija va xatolar faqat rang orqali ifodalanmaydi.
- `MedicineIllustration` — vektor tasvir, namuna quti; undagi kod skanerlash uchun emas.

## Yangilangan ekranlar

Joriy auditoriya — faqat dori xaridorlari. Asosiy navigatsiya: Tekshirish,
Dorixonalar, Ballarim, Yordamchi. Dori qidirish qoʻshimcha menyuda qoladi.
Xodimlar kirishi, inspektor, bojxona va ishlab chiqaruvchi sahifalari bosh sahifaga
vaqtinchalik yoʻnaltiriladi; kodlari kelajak uchun saqlangan. Bu faqat veb interfeys
chegarasi, backend ruxsatlarini almashtirmaydi.
Akkaunt + skan + surat asosidagi yangi ball oqimi `../SCANNER_DATA_PLAN.md` da
belgilangan, hali joriy qilinmagan; mavjud ball mexanizmi demo boʻlib qoladi.

1. Bosh sahifa: kamera, surat, qoʻlda kod va ixtiyoriy Namangan dorixonasini tanlash.
2. Xarita: qidiriladigan roʻyxat, “Yaqinimda”, bonus filtri, tanlangan dorixona va yoʻnalish havolasi.
   Roʻyxat xarita rasmlari yuklanmaganda ham mavjud. API xatosi qayta urinish bilan koʻrsatiladi.
3. Dori qidirish: yirik qidiruv, nom/surat/kod usullari va belgilangan maydonlar.
4. Yordamchi: sodda savol namunalari, oʻqilishi oson suhbat, yuborish va yuklanish holatlari.
5. Tekshiruv natijasi: yumshoq, kontrastli holat kartalari, aniq manba, xato va muvaffaqiyatni ajratish.

Umumiy shrift, ranglar va navigatsiya qolgan veb sahifalariga ham qoʻllanadi.
Native Expo ilovasi va Telegram botining interfeysi bu oʻzgarishga kirmaydi.

## Tekshiruv

Bosh sahifa query parametrlarini serverda oʻqiydi va `ScanHome` interfeysini dastlabki
HTML bilan yuboradi. JavaScript sekin yoki umuman yuklanmasa ham sahifa kutish yozuvida
qolmaydi; tekshirish amallari uchun JavaScript kerak. Shaxsiy query parametrli bosh
sahifa umumiy statik keshga tushmaydi.

- Next.js production build va TypeScript tekshiruvi.
- Chromium: asosiy toʻrtta sahifa 320, 390, 768, 1024 va 1440 px kenglikda gorizontal overflow bermadi.
- Katta matn saqlanishi, 320 px da kattalashtirilgan matn va 200% matn oʻlchamida reflow tekshirildi.
- Qoʻlda kod kiritish, demo backenddan natija, xarita qidiruvi va skanerga dorixona uzatish tekshirildi.
- Dori qidiruvi, yordamchi javobi, kamera ochilmagan holat, xarita API xatosi va retry tekshirildi.
- Sinov backendida alohida vaqtinchalik baza va oʻchirilgan tashqi AI ishlatildi.
- Haqiqiy telefon kamerasi, iOS Safari/VoiceOver va foydalanuvchilar bilan usability sinovi hali kerak.

## Dizayn chegaralari

Frontend rasmiy manbasiz natijani “xavfsiz” deb atamaydi. Backend tekshiruv qoidalari bu ishda
oʻzgarmagan, faqat sotuv qaydi yoʻqligi haqidagi ayblovchi matn neytrallashtirilgan.
Namangan qamrovi, OSM importi va demo natija tafsilotlari `../NAMANGAN_PILOT.md` da.
UI yangilanishi `../PRODUCTION_READINESS.md` dagi ochiq server xavflarini yopmaydi.

Sensorli boshqaruvlar uchun asos: [W3C target size](https://www.w3.org/WAI/WCAG22/Understanding/target-size-enhanced.html).
Bu toʻliq WCAG sertifikatsiyasi emas.
