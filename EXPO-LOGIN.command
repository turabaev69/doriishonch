#!/bin/bash
# iPhone Expo Go uchun: kompyuterda Expo hisobiga kirish (bir marta).
cd "$(dirname "$0")/mobile" || exit 1
echo "Expo hisobingizga kiring (hisob yoʻq boʻlsa: https://expo.dev/signup — bepul)."
echo "Parol yozilayotganda ekranda KOʻRINMAYDI — yozib, Enter bosing."
echo
for i in 1 2 3 4 5; do
  if ./node_modules/.bin/expo login; then
    echo; echo "✅ Kirildi: $(./node_modules/.bin/expo whoami)"
    echo "Endi bu oynani yopishingiz mumkin — DEMO avtomatik qayta ishga tushiriladi."
    exit 0
  fi
  echo; echo "❌ Kirib boʻlmadi. Qaytadan urinib koʻring."; echo
done
