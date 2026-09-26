# DoriIshonch AI — production auditi

Sana: 2026-09-26. Boshlangʻich commit: `51c7fd4`.
Qamrov: asosiy DoriIshonch backend, veb, mobil, Telegram bot va deploy konfiguratsiyasi.
`rentgenai/` alohida loyiha; ushbu production ishlari unga tatbiq etilmagan.

**Qaror: hozircha ommaviy production reliziga tayyor emas.** Bu hujjat kod auditi va lokal
testlarga asoslangan; haqiqiy server, tashqi API, klinik yoki huquqiy validatsiya bajarilmadi.

## Tizimni tushunish

- `frontend/`: Next.js App Router. Kamera, surat yoki qoʻlda kod → `/api/verify`.
- `mobile/`: Expo/React Native; shu backend, lokal tarix va xodim sessiyasi.
- `bot/`: aiogram adapteri; `core.py` mantiqi shu HTTP API orqali ishlaydi.
- `backend/app/services/trace.py`: GS1 kod, reestr, markirovka, sotuv va xaridorlar tarixidan qoidaviy xulosa.
- `services/aslbelgisi.py`, `customs.py`: tashqi adapterlar; mavjud kod integratsiya tasdiqlanganini anglatmaydi.
- `services/ledger.py`: bitta bazadagi SHA-256 zanjir; tarqatilgan konsensus yoki tashqi notarial tasdiq yoʻq.
- `services/ai.py`, `agent.py`, `ml/`: izoh, vositali yordamchi, qadoq va xavf signallari.
- `services/rewards.py`: qurilma ID asosida ball, missiya va mukofotlar; tasdiqlanmagan topilmalar kutiladi.
- `deploy/`: Caddy → Next.js → FastAPI → PostgreSQL. ML fayllari alohida volume da.

Asosiy qiymat: quti qayta sotilayotgani haqida signal berish. Qurilma ID va “sotib oldim”
tugmasi kassa cheki yoki xaridor shaxsining isboti emas. AI yoki kod shakli tekshiruvi
dori tarkibi va haqiqiyligini mustaqil tasdiqlamaydi.

## Birinchi bosqichda yopilgan xavflar

| Muammo | Oʻzgarish |
| --- | --- |
| Eski sxemada `drop_all` production bazasini yoʻqotishi mumkin edi | Production yoki seed oʻchiq rejimda sxema nomuvofiqligi maʼlumotni oʻzgartirmasdan xato beradi |
| Demo loginni yashirish parolni bekor qilmas edi | Productionda demo seed, demo login va demo tokenlar bloklandi |
| `AUTH_ENABLED=false` barcha xodimlar himoyasini oʻchirardi | Production startup buni rad etadi; rol tekshiruvi ham bypass bermaydi |
| Qisqa kalit, HTTP/wildcard CORS va oʻchiq rate limit | Startup tekshiruvi kuchaytirildi; production signing key fayldan avtomatik olinmaydi |
| Rol oʻzgarsa yoki xodim oʻchirilsa, token eski huquqni saqlardi | Productionda har soʻrovda joriy xodim va rol bazadan tekshiriladi |
| Deploy hujjati `.env.production`, konteyner esa `../.env` ishlatardi | Backend/bot uchun yagona `deploy/.env.production`; xavfsiz flaglar Compose da majburiy |
| Haqiqiy admin yaratish yoʻli yoʻq edi | `python -m app.manage create-admin --username operator`; yashirin parol, ustidan yozish yoʻq |
| Production env tasodifan Git ga tushishi mumkin edi | `.env.*` ignore qilinadi, faqat namuna fayllari istisno |

Sxema oʻzgartirilmadi; `SCHEMA_VERSION` oshirilmadi. Demo reset xulqi faqat development va
seed yoqilgan holatda saqlangan. Haqiqiy bazani bunday rejimga ulamang.

## Ochiq reliz bloklovchilari

### P0 — maʼlumot va ruxsat yaxlitligi

1. **Migratsiya va tiklash:** Alembic migratsiyalari yoʻq. Hozirgi himoya maʼlumotni saqlab qoladi,
   ammo yangilanishni oʻzi bajarmaydi. Boshlangʻich sxema, upgrade yoʻli va PostgreSQL zaxiradan
   qayta tiklash mashqi talab qilinadi. Eskirgan bazani avtomatik reset bilan “tuzatish” mumkin emas.
2. **Proksi IP ishonchi:** `security.py:client_ip` ixtiyoriy `cf-connecting-ip` va XFF ning birinchi
   qiymatiga ishonadi. Caddy konfiguratsiyasida ushbu CF sarlavhasini tozalash yoki haqiqiy Cloudflare
   manbalarini tekshirish yoʻq. Soxta header orqali limit aylanib oʻtilishini toʻliq proksi zanjirida
   reproduksiya qilish, chegarada headerlarni normalizatsiya qilish va ishonchli proksilarni cheklash kerak.
3. **Parallel yozish:** `ledger.append` oxirgi ID + 1 ni blokirovkasiz hisoblaydi. Parallel soʻrovlarda
   bir xil ID olinishi va tranzaksiya xatosi xavfi bor. Ledger, xarid va mukofotlar uchun PostgreSQL
   parallel/idempotency testlari, atomik tranzaksiyalar va aniq lock strategiyasi kerak.
4. **Shikoyat egasi:** `/reports` faqat taxmin qilinadigan `scan_id` bilan boshqa skan yozuvini
   oʻzgartira oladi. Anonimlikni buzmagan holda skan egasining imzolangan ruxsati va takroriy
   yuborish himoyasi kerak. Xarid va ballar uchun ham mijoz bergan ID ishonch chegarasi qayta koʻriladi.

### P1 — xavfsiz mahsulot va ekspluatatsiya

5. **Nomaʼlum natija:** rasmiy manba ulanmagan holatda kod tuzilishi yaxshi boʻlsa “ok” yoʻli mavjud
   (`trace._crowd_checks`, `_finish`). Rasmiy tekshiruv yoʻqligi alohida, aniq nomaʼlum holat boʻlishi;
   veb, mobil va bot bir xil maʼnoni koʻrsatishi kerak. Mavjud demo bazani productionga koʻchirmaslik kerak.
6. **Xarid qoidasi:** `LedgerFacts.foreign_purchase` bir dorixonada ikki soat ichidagi boshqa
   qurilma skanini ham bir xaridor deb hisoblaydi. Bu asosiy qayta sotish signalini bostirishi mumkin;
   biznes qoidasi va testlar alohida qayta ishlanadi.
7. **Fayl/AI resurslari:** hajm cheklovi `Content-Length` ga tayanadi; upload endpointlari butun faylni
   oʻqiydi. Oqim boʻyicha limit, tasvir tekshiruvi, AI token/kunlik xarajat chegarasi va timeout kerak.
8. **Maxfiylik:** skan koordinatalari taxminan 100 m gacha saqlanadi va `/map/scans` da ommaviy
   qaytariladi. “Joylashuv saqlanmaydi” degan eski izohlar amaldagi kodga mos emas. Rozilik,
   agregatsiya, saqlash muddati va oʻchirish siyosati ishlab chiqiladi.
9. **Xodim sessiyalari:** veb tokeni localStorage, mobil tokeni AsyncStorage da. XSS/token oʻgʻirlanishi,
   sessiyani bekor qilish va parol almashganda eskisini bekor qilish mexanizmi qayta koʻriladi.
10. **Ishlatish nazorati:** `/health` bazani tekshirmaydi. Readiness, strukturali loglar, request ID,
    metrikalar, alert, backup/restore, rollback va CI release gate kerak. Python dependencies uchun
    takrorlanuvchi lock, konteyner/dependency auditi, frontend non-root runtime ham tekshiriladi.
11. **Haqiqiy integratsiyalar:** Asl Belgisi va bojxona bilan ruxsat, kontrakt testlari, timeout/error
    semantikasi, reestrning toʻliqligi va maʼlumot yangilanishi tasdiqlanishi kerak. Demo testlar yetarli emas.

## Keyingi ish tartibi va qabul mezonlari

1. PostgreSQL migratsiyasi + zaxira/tiklash: mavjud maʼlumotlar va zanjir hashlarini saqlagan upgrade testi.
2. Proksi, anonim ruxsat va ledger: soxta IP header, boshqa skanga shikoyat va parallel yozishga regression testlar.
3. Tekshiruvning ishonch darajasi: rasmiy manba yoʻqligida hech qaysi klient haqiqiylikni tasdiqlamaydi.
4. Staging: yangi baza, haqiqiy admin, HTTPS, cheklangan pilot maʼlumotlar; kamera va bot smoke testlari.
5. Release gate: CI, monitoring, restore mashqi, rollback va domen/server egasining production tasdigʻi.

Domen, hosting, maʼlumot manbalari va xizmatdan foydalanadigan tashkilotlar aniqlashtiriladi.
Chatga parol/API kaliti yuborilmaydi. Haqiqiy deploy ushbu audit davomida bajarilmadi.

## Tekshiruv dalillari

- Oʻzgartirishdan oldin ajratilgan vaqtinchalik bazada: **165 backend testi oʻtdi**.
- Yangi production regression testlarining dastlabki ishga tushishida: **21 failed, 1 passed**;
  startup, demo login va baza saqlanishi muammolari reproduksiya qilindi.
- Tuzatishlardan keyin: **192 backend testi va 15 bot testi oʻtdi** (mos ravishda 333 va 58 warning).
- Veb va mobil TypeScript: `tsc --noEmit --incremental false` xatosiz oʻtdi.
- Production Compose: vaqtinchalik, soxta qiymatlar bilan `config --quiet` xatosiz oʻtdi;
  bu konteyner ishga tushishi yoki server tayyorligi testi emas.
- Administrator CLI `--help` tekshirildi. Haqiqiy bazada hisob yaratilmagan.
- Testlar asl `.env`, ishlayotgan baza yoki tashqi API hisoblariga ulanmaydigan vaqtinchalik nusxada bajariladi.
- Mobil qurilmada E2E, ishlab turgan PostgreSQL va haqiqiy server tekshiruvi hali bajarilmagan.

## Tekshirilgan rasmiy manbalar

- [Docker Compose: konteyner environment va env_file](https://docs.docker.com/compose/how-tos/environment-variables/set-environment-variables/)
- [Caddy reverse_proxy: header va trusted proxy xulqi](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy)
- [Alembic: sxema migratsiyalari](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
