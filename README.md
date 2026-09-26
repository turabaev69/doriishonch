# DoriIshonch

Dori sotib olayotganda qutidagi kodni tekshirish uchun qilayotgan ilovamiz.
Kodni kamera bilan skanerlash, suratdan o‘qish yoki qo‘lda yozish mumkin.
Natijada kod bo‘yicha bor ma’lumot va ogohlantirishlar ko‘rinadi.

Hozircha oddiy xaridorlar uchun ishlayapmiz. Dorixonalar xaritasi Namangan bilan cheklangan.
Maqsad — odam ko‘p yozuv o‘qimasdan, kerakli ma’lumotni tez topishi.

**Bu hali sinov loyihasi.** Kodni tekshirish dori tarkibi yoki uning original ekanini
kafolatlamaydi. Demo dorilar va ularning sotuv tarixi haqiqiy xaridlar emas.

## Hozir nimalar bor?

- Kamera, surat yoki qo‘lda kod kiritib tekshirish.
- Dori nomi, yaroqlilik muddati va ma’lumot manbasini ko‘rsatish.
- Namangan dorixonalarini xaritadan topish va skanerlash uchun tanlash.
- Qutining oldingi skanlari va xarid qaydlarini ko‘rish.
- Xarid narxini kiritish va shu qutidagi dorining boshqa xaridorlar yozgan narxlari bilan solishtirish.
- Dori qidiruvi, yordamchi va sinab ko‘rish uchun namuna kodlar.
- Demo ballar va ball tarixi.

Tekshirish uchun akkaunt shart emas. Hozirgi ballar brauzerdagi anonim qurilma
identifikatoriga bog‘langan demo tizim. Akkauntga kirib, bir qutining kodi va rasmini
yuborish orqali ball yig‘ish hali ishlab chiqilmoqda. Haqiqiy pul yoki chegirma va’da qilinmaydi.

## Ma’lumotlar haqida

Rasmiy Asl Belgisi API’siga ulanish uchun kod yozilgan, lekin haqiqiy kalit va
integratsiya sinovi kerak. Kalitsiz ishlaganda rasmiy tekshiruv bajarildi deb bo‘lmaydi.
Demo natijalari alohida belgilanadi.

“Sotuv qaydi topilmadi” degani mavjud bazada yozuv yo‘qligini bildiradi.
Bu dorixona sotuvni kassadan o‘tkazmaganining isboti emas.

Xarita [OpenStreetMap](https://www.openstreetmap.org/copyright) ma’lumotlaridan
foydalanadi. Namangan pilotiga 44 ta dorixona yozuvi import qilingan.
Ularning ish vaqti, litsenziyasi va dori zaxirasi biz tomonidan tasdiqlanmagan.
Bu yozuvlar Git ichidagi demo bazaga qo‘shilmagan; yangi o‘rnatishda alohida
import kerak. Tartibi [Namangan haqidagi hujjatda](NAMANGAN_PILOT.md) bor.

## Kompyuterda ishga tushirish

Python 3.11 yoki yangiroq versiyasi, Node.js 20+ va npm kerak.
Quyidagi buyruqlar macOS va Linux uchun.

```bash
git clone https://github.com/turabaev69/doriishonch.git
cd doriishonch
cp .env.example .env
```

API kalitlarini hozircha bo‘sh qoldirish mumkin. Asosiy demo, kamera skaneri va
qo‘lda tekshirish ishlaydi. AI javoblari va suratni AI bilan o‘qish uchun alohida kalit kerak.

**Backend — birinchi terminalda:**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend — loyiha papkasida ochilgan ikkinchi terminalda:**

```bash
cd frontend
npm ci
npm run dev
```

Brauzerda http://localhost:3000 ni oching. Backend http://localhost:8000 da ishlaydi.
Telefon kamerasi uchun HTTPS kerak; oddiy lokal IP manzilda kamera ochilmasligi mumkin.

Faqat yangi lokal demo uchun qisqa yo‘l ham bor: `./start.sh dev`.
`./start.sh public` vaqtinchalik HTTPS tunnel ochadi. Bu doimiy hosting o‘rnini bosmaydi.
Ishlayotgan serverda bu buyruqlarni qayta ishga tushirmang — mavjud jarayonlarni to‘xtatishi mumkin.

## Papkalar

| Papka | Ichida nima bor |
| --- | --- |
| `frontend/` | Next.js, TypeScript va Tailwind bilan yozilgan veb ilova |
| `backend/` | FastAPI, tekshiruv qoidalari, ma’lumotlar bazasi va testlar |
| `bot/` | Telegram bot uchun qo‘shimcha kod |
| `mobile/` | Expo asosidagi mobil prototip |
| `ml/` | Qadoq modelini o‘qitish tajribalari |
| `deploy/` | Docker va server sozlamalari |

Hozir asosiy ish veb ilovaning xaridor qismida. Xodimlar panellari kodi saqlangan,
lekin veb menyudan olib tashlangan. Bot va mobil prototip vebdagi eng so‘nggi o‘zgarishlar
bilan bir xil deb hisoblanmasin.

## Narxlar qanday solishtiriladi?

Skanerdan keyin “Necha pulga sotib oldingiz?” deb so‘raladi. Butun quti narxini
so‘mda yozasiz yoki “Hozir emas”ni bosasiz. Faqat bir xil quti kodi, oxirgi 90 kun
va Namangan dorixonalari bo‘yicha solishtiramiz. Kamida uchta boshqa xaridor narxi
kerak; demo va takroriy yozuvlar qo‘shilmaydi.

Narxlar chek bilan tasdiqlanmagan. Dorixona reytingi hali yo‘q — bu ma’lumotlar
uning keyingi asosi bo‘ladi. Hisoblash va cheklovlar [PRICE_DATA.md](PRICE_DATA.md) da.

## Tekshirish

```bash
cd backend
.venv/bin/python -m pytest -q
```

Testlar alohida vaqtinchalik bazada ishlaydi.

Frontendni yig‘ish:

```bash
cd frontend
npm run build
```

## Keyingi ishlar

- Ballarni qurilmaga emas, xaridor akkauntiga bog‘lash.
- Skan qilingan qutining rasmini rozilik bilan saqlash.
- Takroriy skanlar va noto‘g‘ri ball yig‘ishni cheklash.
- Rasmiy markirovka tizimi bilan haqiqiy ma’lumotlarda sinov qilish.
- Yetarli va tekshirilgan rasmlar yig‘ilgach, qadoq modelini yaxshilash.

Rejaning batafsil ko‘rinishi: [skaner ma’lumotlari va ballar](SCANNER_DATA_PLAN.md).

## Serverga chiqarishdan oldin

Loyiha hali to‘liq productionga tayyor emas. Ochiq muammolar va deploy tartibi
[PRODUCTION_READINESS.md](PRODUCTION_READINESS.md) da yozilgan.
Haqiqiy xizmatda demo bazadan foydalanmang, avtomatik demo to‘ldirishni o‘chiring
(`SEED_ON_STARTUP=false`) va bazaning zaxirasini oling.

`.env`, API kalitlari, bot tokeni, `.secret`, foydalanuvchi rasmlari va ishlayotgan
bazani GitHub’ga yuklamang. Repodagi `.env.example` faqat bo‘sh sozlamalar namunasi.
