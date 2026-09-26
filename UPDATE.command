#!/bin/bash
# Saytni yangi kod bilan qayta ishga tushiradi, HTTPS manzil (tunnel) OʻZGARMAYDI.
cd "$(dirname "$0")" || exit 1
echo "🔄 DoriIshonch yangilanmoqda (manzil oʻzgarmaydi)…"
if [ backend/requirements.txt -nt backend/.venv/.installed ]; then
  backend/.venv/bin/pip install -q -r backend/requirements.txt && touch backend/.venv/.installed
fi
if [ frontend/package.json -nt frontend/node_modules/.installed ]; then
  (cd frontend && npm install --no-audit --no-fund && touch node_modules/.installed)
fi
echo "🔨 Sayt yigʻilmoqda (1-2 daqiqa)…"
(cd frontend && npm run build >/tmp/doriishonch-build.log 2>&1) || { echo "❌ Yigʻishda xato: /tmp/doriishonch-build.log"; read -r; exit 1; }
for port in 8000 3000; do
  for pid in $(lsof -ti tcp:$port -sTCP:LISTEN 2>/dev/null); do
    cmd="$(ps -o command= -p "$pid")"
    echo "$cmd" | grep -Eq "uvicorn app.main|next-server|next start" && kill "$pid"
  done
done
sleep 1
(cd backend && nohup .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 >/tmp/doriishonch-backend.log 2>&1 &)
(cd frontend && nohup npx next start --port 3000 --hostname 0.0.0.0 >/tmp/doriishonch-frontend.log 2>&1 &)
echo "⏳ Server ishga tushmoqda (baza yangilansa ~1 daqiqa)…"
for _ in $(seq 1 120); do curl -s http://127.0.0.1:8000/health >/dev/null 2>&1 && break; sleep 1; done
for _ in $(seq 1 30); do curl -s -o /dev/null http://127.0.0.1:3000/ && break; sleep 1; done
echo "✅ Tayyor: $(sed -n 's/^SAYT: //p' DEMO-URL.txt)"
echo "Bu oynani yopsangiz ham sayt ishlashda davom etadi."
