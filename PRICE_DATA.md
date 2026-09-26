# Xarid narxlari

Skan natijasida “Necha pulga sotib oldingiz?” degan ixtiyoriy savol chiqadi.
Narx butun quti uchun, soʻmda kiritiladi. “Hozir emas” bilan oʻtkazish mumkin.
Kod, suratdan olingan kod va GTIN/seriyani alohida kiritish usullari ishlaydi.

## Saqlash

- Narx mavjud `consumer_scans.price_paid` maydoniga yoziladi. Yangi sxema yoki baza reseti kerak emas.
- Shu skanni yaratgan anonim qurilma IDʼsi talab qilinadi. Bu haqiqiy akkaunt tasdigʻi emas.
- Butun son: 1–100 000 000 soʻm. Yetti kundan eski skanga narx qabul qilinmaydi.
- Bir skanga bir narx: aynan bir soʻrovni takrorlash yozuvni koʻpaytirmaydi; boshqa narx 409 qaytaradi.
- Narx saqlash yangi skan, xarid bloki yoki bonus ball yaratmaydi. Ledger oʻzgarmaydi.
- Narx skandagi dorixona, quti kodi va skan vaqtiga bogʻlangan. Dorixona tanlanmagan narx saqlanadi,
  ammo Namangan taqqoslashiga qoʻshilmaydi. Bu kassa cheki yoki tasdiqlangan sotuv emas.

## Taqqoslash

- Faqat aynan bir GTIN — boshqa doza, quti hajmi yoki nomi oʻxshash dori aralashtirilmaydi.
- Oxirgi 90 kundagi Namangan dorixonalari; soʻnggi 5000 ta mos nomzod yozuv koʻrib chiqiladi.
- Xaridorning oʻz narxlari chiqarib tashlanadi. Boshqa har bir qurilmadan eng soʻnggi narx olinadi.
- Bir xil seriyali quti takror sanalmaydi. Demo dorilar va demo dorixonalar qatnashmaydi.
- Kamida uchta boshqa qurilma narxi boʻlsa, mediana va undan foiz farqi koʻrsatiladi.
  Yetarli maʼlumot boʻlmasa taxminiy narx chiqarilmaydi.

Bu hali dorixona reytingi emas. Qurilma IDʼsi almashtirilishi, narx esa notoʻgʻri
kiritilishi mumkin. Reytingdan oldin akkaunt, chek/quti dalili, suiisteʼmolni aniqlash,
narxni tuzatish jarayoni va yetarli namuna soni kerak. Katta bazada GTIN va narxlar
uchun alohida indekslangan jadvalga xavfsiz migratsiya rejalashtirilishi kerak.
