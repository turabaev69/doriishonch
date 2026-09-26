# DoriIshonch AI

Xaridor dori qutisini skanerlaydi: quti qayerdan kelgan, bojxonadan oʻtganmi, oldin sotilmaganmi (qayta
ishlatilgan quti sxemasiga qarshi). Qoʻshimcha: bojxona integratsiyasi, inspektor paneli, dori Ishonch kartasi.

## Stack
- backend/: Python 3.11+, FastAPI, SQLAlchemy 2. Mahalliy rejimda SQLite, docker-compose da PostgreSQL 16.
- Qidiruv: rapidfuzz (imlo xatolariga chidamli). pgvector keyinroq qoʻshilishi mumkin.
- frontend/: Next.js 15 (App Router), TypeScript, Tailwind 4
- bot/: aiogram 3. Mantiq bot/core.py da (Brain: hodisa → javoblar, aiogram ga bogʻliq emas), bot.py faqat Telegram adapteri.
  Bot testlari (bot/tests) haqiqiy backend ilovasiga httpx.ASGITransport orqali ulanadi.
- AI: Anthropic Claude API (vision + matn), model nomi .env da (ANTHROPIC_MODEL).
  Kalit boʻlmasa, AI siz rejim: tushuntirish shablondan, surat tanish oʻchadi.

## Tuzilma
- backend/app/main.py — dori katalogi endpointlari (qidiruv, karta, analog, explain, scan)
- backend/app/services/catalog.py — qidiruv, Ishonch kartasi faktlari, analoglar
- backend/app/services/ai.py — Claude bilan tushuntirish (RAG), surat tanish, mavzu toifalash
- backend/app/services/safety.py — tibbiy savollarni bloklash, javob filtri
- backend/app/services/codes.py — GS1 DataMatrix (Asl Belgisi) parser
- backend/app/services/trace.py — quti tekshiruvi: qoidalar → xulosa (ok/warning/danger), qutining yoʻli
- backend/app/services/aslbelgisi.py — haqiqiy Asl Belgisi xTrace Open API ulagichi (ASL_BELGISI_API_KEY)
- backend/app/services/ledger.py — DoriIshonch zanjiri (SHA-256 hash-chain): skanerlash, sotib olish, xabar bloklari
- backend/app/services/places.py — OpenStreetMap Overpass: yaqin haqiqiy dorixonalar
- backend/app/services/agent.py — Claude tool-use agentlari: xaridor yordamchisi, inspektor copiloti
- backend/app/routes_ai.py — /ai/chat, /ai/inspector (login), /ai/inspect-box (vision), /ai/status
- backend/app/auth.py — xodimlar login (HMAC token, rollar); xaridorlar anonim
- mobile/ — Expo (React Native) iOS/Android ilova; mobile/AGENTS.md ga amal qiling. src/app/_layout.tsx = Stack,
  src/app/(tabs)/ = tablar (asosiy, tarix, ballar, AI, koʻproq), batafsil sahifalar src/app/ da. Tarix va xodim
  sessiyasi faqat qurilmada (src/lib/store.ts).
- backend/app/ml/ — oʻz modellarimiz: risk_features.py (22 belgi) + risk_synth.py (simulyatsiya) + risk_model.py
  (HistGradientBoosting, monoton, occlusion tushuntirish) + learning.py (inspektor tasdigʻidan qayta oʻqitish, demo
  backfill); packnet.py (qadoq CNN, numpy inference), weights/packnet-v1.json. routes_ml.py — /ml/status, /ml/retrain,
  /ml/packnet/check, /ml/packnet/weights
- ml/packnet/ — PackNet oʻqitish (torch, faqat ishlab chiqishda): boxes.py (sintetik qutilar), train.py, make_samples.py
- backend/app/regions.py — 14 hudud; routes_map.py — /map/pharmacies (ommaviy, xavfsiz), /map/regions, /map/inspector (xavf)
- backend/app/services/customs.py — bojxona adapterlari, deklaratsiyani moslash/tekshirish/roʻyxatga olish
- backend/app/services/risk.py — dorixonalar xavf signallari + IsolationForest
- backend/app/routes_trace.py — /verify, /reports, /customs/*, /inspector/* (reports/{id}/resolve, batch-signals), /demo/codes
- backend/app/services/rewards.py + routes_rewards.py — ballar, missiyalar, reyting, mukofotlar (anonim hamyon = device_hash)
- backend/app/seed_trace.py — demo ishtirokchilar, qutilar, hodisalar va 12 ta stsenariy (DEMO_SCENARIOS)
- backend/seed/*.csv — demo dori maʼlumotlari (seed.py yuklaydi); customs_feed.json — demo bojxona oqimi
- frontend/app/page.tsx — skaner (bosh sahifa); components/CameraScanner.tsx — @zxing/browser

## Qoidalar
- UI va AI javoblari oʻzbek tilida (lotin).
- Ishonch kartasi hech qachon ball, reyting yoki "eng yaxshi" soʻzini koʻrsatmaydi.
- Har bir fakt manba URL va yangilangan sana bilan saqlanadi va koʻrsatiladi.
- AI faqat bazadagi faktlar asosida javob beradi (RAG). Doza, tashxis, davolash tavsiyasi bermaydi.
- Quti xulosasini faqat qoidalar chiqaradi; AI xulosani oʻzgartirmaydi, faqat tushuntiradi.
- Inspektor signallari "isbot emas, tekshiruv uchun signal" deb koʻrsatiladi; hech kim aybdor deb eʼlon qilinmaydi.
- Zanjir bloklarini hech qachon UPDATE/DELETE qilmang; faqat ledger.append. Demo reset = bazani qayta yaratish.
- Frontend API ni /api orqali chaqiradi (next.config.ts rewrites → BACKEND_URL, standart 127.0.0.1:8000).
- Bazada vaqt UTC; foydalanuvchiga UTC+5 (DISPLAY_UTC_OFFSET_HOURS) koʻrsatiladi.
- Sxema oʻzgarsa, seed.py dagi SCHEMA_VERSION ni oshiring (demo baza qayta yaratiladi).
- Demo maʼlumotlar `is_demo=true` bilan belgilanadi. Demo ishlab chiqaruvchi va brend nomlari toʻqima;
  haqiqiy kompaniya nomini soxta sertifikat bilan hech qachon ishlatmang.
- Xodimlar endpointlari require_role(...) bilan himoyalanadi; xaridor endpointlari (verify, reports, ai/chat) ochiq.
- AI testlari haqiqiy API ni chaqirmaydi: ai._client ni soxta client bilan almashtiring (tests/test_ai_agent.py).
- Har bir endpoint uchun pytest test yoziladi.
- security.py: rate-limit (IP boʻyicha, cf-connecting-ip), xavfsizlik sarlavhalari; ENVIRONMENT=production da
  check_production_config() notoʻgʻri sozlamada serverni toʻxtatadi. Testlarda RATE_LIMIT_ENABLED=false.
- Oʻz modellar xulosani oʻzgartirmaydi (ai_risk — signal). Belgi qoʻshsangiz: FEATURES, risk_synth va NEUTRAL/REASONS
  ni birga yangilang (karta features mos kelmasa, model qayta oʻqitiladi).
- PackNet inference uch joyda bir xil: backend/app/ml/packnet.py, frontend/lib/packnet.ts, mobile/src/lib/packnet.ts
  (oxirgi ikkisi aynan bir fayl). interpret() mantiqini uchalasida birga oʻzgartiring. Model qayta oʻqitilgach
  make_samples.py ni ishga tushiring (ogʻirliklarni veb/iPhone ga nusxalaydi).
- UI matnlari oddiy tilda: foydalanuvchiga hash, blok #, GTIN, DataMatrix kabi texnik soʻzlarni koʻrsatmang.
- Ball qoidalari rewards.py boshida. "Topdim" (catch/report) ballari faqat inspektor tasdigʻidan keyin hisoblanadi.
  Missiya matnida dorixona hech qachon "xavfli" deb atalmaydi.
- mobile: dizayn tokenlari src/lib/theme.ts, umumiy komponentlar src/components/ui.tsx (Button, Card, Row, Gradient…).
  mobile/.npmrc da legacy-peer-deps=true (Expo SDK paketlari peer ziddiyati uchun).

## Buyruqlar
- ./start.sh (tayyor rejim), ./start.sh public (HTTPS tunnel), ./start.sh mobile, ./start.sh bot, ./start.sh dev, ./start.sh test, ./start.sh reset
- .env da TELEGRAM_BOT_TOKEN boʻlsa, bot ./start.sh bilan birga ishga tushadi
- cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload
- cd backend && pytest
- cd frontend && npm install && npm run dev
- docker compose up --build   (Postgres bilan hammasi)
- Production: cd deploy && docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build (Caddy HTTPS)
- ./start.sh iphone yoki DEMO.command — tunnel + Expo QR (mobile/.env ga EXPO_PUBLIC_API_URL yoziladi)
- Bazani qayta yaratish: backend/doriishonch.db faylini oʻchiring
