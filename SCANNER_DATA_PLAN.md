# Skaner → akkaunt → ball → tekshirilgan qadoq maʼlumotlari

Tadqiqot sanasi: 2026-09-26. Holat: kod auditi va amalga oshirish loyihasi.
Bu hujjatdagi yangi login, foto-dataset va reward v2 hali joriy qilinmagan.
Rasmiy Asl Belgisi API kaliti mavjud emas; haqiqiy servis bilan tekshirish bajarilmagan.

## Tasdiqlangan MVP chegarasi

Foydalanuvchi aniqlashtirishi: hozir dastur faqat oddiy dori xaridorlari uchun.
Inspektor, bojxona, ishlab chiqaruvchi va dorixona xodimi uchun yangi akkaunt/panel
ishlab chiqilmaydi. Mavjud modullar oʻchirilmaydi, keyingi bosqichga qoldiriladi.
Quyidagi moderatsiya talablari ommaviy yangi rol emas, maʼlumot sifati nazorati.

Asosiy oqim: xaridor kiradi → dori sotib olayotganda quti kodini skanerlaydi →
shu qutini suratga oladi → server ikkala dalilni bitta hissaga bogʻlaydi →
qoidalarga mos hissa uchun ball akkauntga yoziladi. Skan yoki suratning oʻzi
yangi ball olish uchun yetmaydi. Kod-surat mosligi noaniq boʻlsa ball kutiladi.
Oddiy xavfsizlik tekshiruvi loginsiz va foto-datasetga roziliksiz ham mavjud.
Ball dorini koʻproq sotib olishga emas, takrorlanmagan sifatli hissaga beriladi.
Quti surati xarid cheki emas; shu asosda «xarid rasmiy tasdiqlandi» deyilmaydi.

Bu yangi reward qoidasi hali backendga kiritilmagan. Eski demo skan/mission/report
bonuslari yangi pilot qoidalariga koʻchirib qoʻyilmaydi.

## 1. Hozir dasturda nima bor?

- `frontend/lib/device.ts`: tasodifiy qurilma identifikatori localStorageʼda saqlanadi.
  Telefon/brauzer almashtirilsa hamyon davomiyligi yoʻqolishi mumkin.
- `backend/app/auth.py`: faqat xodimlar autentifikatsiyasi; xaridor akkaunti yoʻq.
- `backend/app/models.py`: Wallet va PointEvent qurilma hashiga bogʻlangan.
- `backend/app/routes_rewards.py`: hamyon va mukofot soʻrovlarida mijoz yuborgan device_id
  ishlatiladi. Bu tasdiqlangan akkaunt egasi ekanining isboti emas.
- `backend/app/services/rewards.py`: takrorlarni ilova darajasida qidiradi, ammo
  PointEvent jadvalida takroriy mukofotni toʻsadigan unique cheklov yoʻq. Parallel
  soʻrovlar va mukofot yechishni tranzaksiyali tekshirish kerak.
- `backend/app/routes_trace.py`: suratdan kod olinadi; qadoq suratini rozilik bilan
  uzoq muddatli datasetga saqlash oqimi yoʻq.
- ConsumerScan skaner hodisasini, CrowdProduct esa yangi mahsulot kodini saqlaydi.
  Yangi mahsulot, yangi individual quti va yangi surat uch xil tushuncha.
- `backend/app/services/aslbelgisi.py`: kod maʼlumoti/tarixini soʻraydi;
  alohida toʻliq kod validatsiyasi mavjud emas. Tekshiruvlari MockTransport bilan.
- `backend/app/services/trace.py`: 91/92 maydonlarining mavjudligi `crypto_present`
  nomli yashil tekshiruvga aylantiriladi. Mavjudlik tekshirilgan imzo degani emas;
  bu axborot holati boʻlishi, tasdiqlanmaganligi aniq yozilishi kerak.
- `ml/packnet/train.py`: sintetik maʼlumotlar, oldindan belgilangan demo sinflar.
  `--real` suratlarni treningga qoʻshadi, lekin validatsiya toʻplami sintetik qoladi.
  Nomaʼlum haqiqiy GTIN yangi sinfga emas, OTHER sinfiga tushadi. Hozirgi modelni
  haqiqiy dorilar originalligini tasdiqlovchi model deb ishlatib boʻlmaydi.

## 2. Foydalanuvchi uchun sodda oqim

1. Qutini skanerlaydi. Login natijani koʻrishga toʻsiq boʻlmaydi.
2. Natijadan keyin: «Ball yigʻish uchun kiring».
3. Login orqali bitta akkaunt ochiladi; keyingi qurilmada ham shu hamyon ochiladi.
4. Tekshiruv natijasi darhol koʻrsatiladi. Ball uchun shu qutining surati ham kerak;
   qayta skanerlash ballni koʻpaytirmaydi.
5. «Ball uchun quti suratini qoʻshish»:
   old tomoni va partiya/muddati yozilgan tomoni. Kodli tomon kerak boʻlsa alohida.
6. Suratning aniqligi tekshiriladi; xira boʻlsa qayta olish taklif qilinadi.
7. Suratni saqlash va model oʻqitishida foydalanish uchun alohida, oldindan
   belgilanmagan rozilik beriladi. Rad etish oddiy tekshiruvni cheklamaydi.
8. Kod va surat bitta hissada tekshirilgach ball hisoblanadi yoki tekshiruvni kutadi.
   «Ballarim» sahifasida mavjud ball, kutilayotgan ball va harakatlar tarixi koʻrinadi.

«Yangi quti topdingiz» faqat GTIN + individual seriya boʻyicha aniqlanadi.
GTIN bir xil mahsulotning koʻplab qutilarida bir xil boʻlishi mumkin.
«Bazada yoʻq» — «qalbaki» degani emas.

## 3. Login va ballning ishonch chegarasi

Login provayderi tanlanadi: Telegram, SMS OTP yoki email. Har birining konfiguratsiyasi
va tiklash yoʻli kerak; UI tugmasini qoʻshishning oʻzi haqiqiy login emas.

- ConsumerAccount va provayder identifikatori xodimlar rollaridan ajratiladi.
- Server tasdiqlagan sessiyadan account_id olinadi; body/queryʼdagi user_id qabul
  qilinmaydi. Telegram user IDʼni oddiy yuborish ham tasdiq hisoblanmaydi.
- Veb sessiyasi Secure, HttpOnly, SameSite cookie; holat oʻzgartiruvchi soʻrovlarda
  CSRF/Origin tekshiruvi. Login challenge muddati, bir martalik foydalanish, limitlar.
- Telefon/Telegram akkaunti insonning yagona akkaunti ekanini kafolatlamaydi;
  akkauntlararo takrorlar, kunlik limit va shubhali faollik nazorati ham kerak.
- Login oldidagi yangi skanni olish uchun qisqa muddatli server bergan, mehmon
  sessiyasiga bogʻlangan bir martalik claim ishlatiladi. Faqat scan_id yetarli emas.
- Eski device_id ni bilish orqali eski ballarni boshqa akkauntga koʻchirish mumkin
  emas. Demo ballari alohida qoladi; eski ball migratsiyasi alohida tasdiqlanadi.
- Taklif etiladigan reward kaliti: `(account_id, pack_fingerprint, reward_kind,
  campaign_id)`, bazada UNIQUE. Bir individual qutining takroriy mukofoti global
  cheklov bilan ham nazorat qilinadi. Parallel soʻrovlar bitta tranzaksiyada ishlaydi.
- Account hamyon qatori lock qilinadi; ball yechish, balans va event bitta
  tranzaksiyada. PostgreSQL parallel testlari SQLite testlarini toʻldiradi.
- Pul/chegirma beradigan real hamkorlik ulanmaguncha mukofot katalogi demo qoladi.

Ball qoidasi: skan va surat alohida yoziladi, lekin ikkalasi bitta xaridor hissasini
toʻldirgandagina bitta mukofot yaratiladi. Nomaʼlum kod yoki surat uchun darhol
sarflanadigan ball emas, moderatsiya kutadigan
hissa yaratiladi. Faqat «original» deb belgilashga mukofot berilmaydi: bu notoʻgʻri
yorliqlar va datasetni zaharlashga ragʻbat yaratadi. Aniq ball miqdori keyin belgilanadi.

## 4. Haqiqiylikni qanday tekshiramiz?

### Rasmiy manbalardan topilganlar

Oʻzbekistondagi dori markirovkasi odatiy havolali QR emas, GS1 DataMatrix.
Asl Belgisi tavsifida mahsulot, individual quti va tekshiruv qismlari ajratilgan.
[Asl Belgisi: dori kodining tuzilishi](https://help.crpt-turon.uz/hc/ru/articles/5574317718545).
GS1 ham tibbiy mahsulot identifikatsiyasi va kuzatuvi uchun DataMatrixʼni koʻrsatadi.
[GS1 Healthcare](https://www.gs1.org/industries/healthcare/2d-barcode-healthcare).

xTrace v1.45.0 hujjatining 9.4 boʻlimida
`POST /public/api/v1/code-verification/verify` bor: toʻliq kod, shu jumladan
ajratgichlar bilan yuboriladi; javobda `verified` va `productGroup` qaytadi.
Bu mahsulot tarkibining laboratoriya tasdigʻi emas. Joriy adapter bu metodni
chaqirmaydi. Hujjat jadvali va misolida soʻrov konverti bir xil aniqlikda berilmagan:
test muhitida JSON shaklini contract-test orqali tasdiqlash kerak, taxminni yashirmaymiz.
[Rasmiy xTrace Open API](https://help.crpt-turon.uz/hc/en-us/articles/36078638174481-xTrace-Open-API-Description),
[v1.45.0 PDF, 112–114-betlar](https://help.crpt-turon.uz/hc/en-us/article_attachments/50641506296721).

API integratsiyasi uchun tegishli kalit/huquqlar kerak; batafsil tarixga kirish
ishtirokchining huquqlariga bogʻliq. Public soʻrov barcha egalar tarixini kafolatlamaydi.
[xTrace kirish chegaralari](https://help.crpt-turon.uz/hc/en-us/articles/36078638174481-xTrace-Open-API-Description).

Oʻzbekiston farmatsevtika nazorati aniqlangan yaroqsiz va qalbakilashtirilgan
mahsulotlar roʻyxatlarini eʼlon qiladi. Roʻyxatga tushmaganlik asl ekanini isbotlamaydi.
[Rasmiy ogohlantirishlar](https://www.uzpharm-control.uz/ru/pages/information-on-identified-falsified-and-substandard-unsuitable-drugs-and-medical-products).

WHOʼga koʻra skrining natijasi dastlabki signal; ayrim xulosalar tasdiqlovchi
analitik tekshiruvni talab qiladi. Rasmiy etalon qadoq foydali, lekin surat kimyoviy
tarkibni aniqlamaydi.
[WHO: shubhali namunalarni tekshirish](https://www.who.int/docs/default-source/medicines/norms-and-standards/guidelines/quality-control/trs1010-annex5-testing-suspect-samples.pdf?sfvrsn=df47cb5_2).

### Taklif etiladigan tekshiruv qatlamlari

1. Kodni buzmasdan oling: asl baytlar/GS ajratgich, skaner turi, parser versiyasi.
   Havolani avtomatik ochmang. Nazorat raqami faqat tuzilish tekshiruvi.
2. Toʻliq kod boʻlsa rasmiy validatsiya. Qoʻlda kiritilgan GTIN/seriya yoki OCR natijasi
   toʻliq himoyalangan kod sifatida koʻrsatilmaydi; AI kriptoqism yaratmaydi.
3. Kod maʼlumotidan muomala/sotuv holati, muddati, partiya va mos mahsulot tekshiriladi.
4. Mahsulot reestri va yangilangan partiya ogohlantirishlari alohida solishtiriladi.
5. Kod, etalon mahsulot va qutidagi nom/doza/ishlab chiqaruvchi mosligi tekshiriladi.
6. Takroriy skanlar signal beradi, hukm emas. Bir qutini bir necha marta tekshirish
   normal holat; nusxalangan haqiqiy kod ham rasmiy bazada mavjud boʻlishi mumkin.
7. Har bir manba uchun tekshiruv vaqti, natija, maʼlumotning yangiligi va xato turi
   saqlanadi. Timeout, 401/403, 429 yoki notoʻgʻri JSON «kod soxta»ga aylantirilmaydi.
8. Oddiy UI: «Kod rasmiy tizimda tasdiqlandi», «Maʼlumotlar mos kelmadi» yoki
   «Hozir tasdiqlab boʻlmadi». «100% original/xavfsiz» vaʼdasi berilmaydi.

Etalon surat faqat ishlab chiqaruvchi/regulyator/tekshirilgan hamkor manbasidan,
foydalanish huquqi va qadoq versiyasi bilan olinadi. Internetdagi tasodifiy rasm
yoki koʻpchilik yuklagan surat avtomatik ravishda etalon hisoblanmaydi.

## 5. Dataset: yigʻish, tekshirish, oʻqitish

Taklif etiladigan alohida yozuvlar:

| Yozuv | Asosiy vazifa |
|---|---|
| ConsumerAccount / AuthIdentity / Session | Tasdiqlangan akkaunt va sessiya |
| ScanObservation | Kod barmoq izi, mahsulot/quti identifikatori, skan usuli, vaqt |
| AccountScan | Akkaunt bilan yopiq bogʻlanish; ochiq kuzatuvdan ajratiladi |
| ProviderVerification | Rasmiy javob, manba, vaqt, holat, tekshirilgan qamrov |
| PhotoAsset | Yopiq fayl kaliti, tomon, sifat, hash, rozilik va kuzatuvga bogʻlanish |
| ConsentReceipt | Maqsad, versiya, berilgan va bekor qilingan vaqt |
| DatasetReview | Yorliq, dalil, tekshiruvchi, qadoq versiyasi va audit |
| RewardEvent | Account, idempotency kaliti, pending/credited/reversed hodisalari |
| DatasetRelease | Oʻzgarmas manifest, split guruhlari, rozilik holati, model versiyasi |

- Quti old tomoni + partiya/muddat tomoni; surat olishdan oldin yuz, retsept, chek,
  ism/telefon tushirmaslik haqida oddiy eslatma. GPS majburiy emas.
- MIMEʼga ishonmasdan faylni dekodlash, bayt/piksel limiti, qayta JPEG/PNG kodlash,
  EXIF/GPSʼni olib tashlash; fayllar public katalogga joylanmaydi.
- Hash takrorni, perceptual hash oʻxshash suratlarni aniqlash uchun. Surat boshqa
  qutiga qayta biriktirilsa avtomatik bonus yoʻq; inson koʻrib chiqishi kerak.
- Toʻliq serial/kodlar ommaviy tarqatilmaydi. Tekshiruvga kerak raw kod yopiq,
  shifrlangan saqlanadi; dedup uchun server HMAC identifikator ishlatiladi.
- Oʻqitish eksportiga telefon, akkaunt, aniq geolokatsiya kirmaydi. Model serialni
  yodlab olmasligi uchun individual kodlar vizual model nusxasida berkitiladi.
- Yorliqlarni ajratish: mahsulot mosligi, qadoq mosligi, kod validatsiyasi,
  rasmiy qaytarib olish va laboratoriya/ekspert xulosasi. User aytgan «asl» ground truth emas.
- Real/sintetik alohida. Bir fizik qutining barcha suratlari bitta splitda; imkon
  boricha partiya/manba/sana ham ajratiladi. Yangi batch va telefonlarda holdout.
- Avval surat sifati va mahsulotni tanish; keyin etalon bilan farqlar. «Tanilmadi»
  javobi majburiy. Nomaʼlum mahsulot avtomatik «qalbaki»ga aylantirilmaydi.
- Har uploadʼdan online qayta oʻqitish yoʻq: moderatsiya → versiyali dataset →
  offline trening → mustaqil haqiqiy test → tasdiq → shadow rollout → kuzatuv/rollback.
- Oʻlchovlar: mahsulot mosligi, nomaʼlumni rad etish, notoʻgʻri ijobiy/salbiy signal,
  qadoq versiyalari kesimi, kechikish. Faqat sintetik accuracy release mezoni emas.

## 6. Maxfiylik va bolalar

7–70 yosh uchun qulay UI bolalardan avtomatik shaxsiy maʼlumot olishga ruxsat emas.
Amaldagi qonunning 21-moddasida voyaga yetmaganlar maʼlumotlari uchun qonuniy vakil
roziligi koʻrsatilgan. Akkauntga bogʻlangan dori tarixi sezgir boʻlishi mumkin:
maqsad, saqlash muddati, bekor qilish/oʻchirish, joylashtirish va transchegaraviy
uzatish masalalari productiondan oldin mahalliy mutaxassis bilan baholanadi.
[LexUZ: Shaxsga doir maʼlumotlar toʻgʻrisida](https://lex.uz/docs/4396419).

Rozilik bekor qilinsa yangi eksportlardan chiqarish, asl fayl va hosila nusxalarni
oʻchirish jarayoni kerak. Oldin oʻqitilgan modelga taʼsiri release manifest orqali
kuzatiladi; «model darhol unutadi» deb vaʼda berilmaydi. Ledgerʼga shaxsiy maʼlumot
yoki surat kiritilmaydi; mavjud append-only kuzatuv qoidasi buzilmaydi.

## 7. Amalga oshirish tartibi va qabul mezonlari

1. Login provayderi, doimiy HTTPS domen va sessiya/tiklash siyosatini tanlash.
2. Baza backupi va qoʻshimchali migratsiya. SCHEMA_VERSIONʼni oshirib demo reset
   qilish bu vazifa uchun yaramaydi: mavjud skanlar va ballar saqlanishi kerak.
3. Account + server sessiya + account hamyoni; brauzerlararo bir balans,
   boshqa akkaunt maʼlumotiga kirishni rad etish, parallel skan uchun bir mukofot.
4. Signed guest claim va eski device hamyonlaridan xavfsiz oʻtish.
5. Rozilik + yopiq foto upload + moderatsiya. Begona scan_id bilan fayl ulash rad
   etilishi, limitlar va rozilikni bekor qilish testlari.
6. Asl Belgisi stage kaliti/rollari bilan validatsiya + kod maʼlumoti contract-testlari.
   Notoʻgʻri kod, kam huquq, timeout, 429, eskirgan/teskari status va nusxa kod sinovlari.
7. Manbali etalon kutubxonasi va rozilikli real pilot dataset. Shu paytgacha
   model demo holatida, real originallik boʻyicha daʼvo yoʻq.
8. Faqat keyin tasdiqlangan real test va model release. Login/ball uchun ML shart emas.

Ochiq qarorlar: login usuli; Asl Belgisiʼga qonuniy kirish/kalit; etalon qadoq
hamkori; maʼlumot saqlash siyosati va server joylashuvi; haqiqiy mukofot hamkorlari.
API kalitlarini chatga yubormasdan serverning secret konfiguratsiyasiga joylash kerak.
