#!/usr/bin/env bash
# DoriIshonch AI — bitta buyruq bilan ishga tushirish (macOS / Linux)
#
#   ./start.sh           tayyor (production) rejim: http://localhost:3000 va shu Wi-Fi dagi telefonlar uchun
#   ./start.sh public    + internetdan HTTPS manzil (telefon kamerasi uchun), Cloudflare tunnel orqali
#   ./start.sh dev       ishlab chiqish rejimi (kod oʻzgarsa avtomatik yangilanadi)
#   ./start.sh test      backend testlari
#   ./start.sh reset     demo bazani oʻchirib, qaytadan yaratish
#   ./start.sh mobile    iPhone/Android ilova (Expo Go orqali), backend alohida ishlab turishi kerak
#   ./start.sh bot       faqat Telegram bot (backend alohida ishlab turishi kerak)
#   ./start.sh iphone    HAMMASI: server + veb + HTTPS tunnel (sayt kamerasi) + iPhone ilova (Expo Go, QR)
#
# .env da TELEGRAM_BOT_TOKEN boʻlsa, Telegram bot oddiy va public rejimlarda ham avtomatik ishga tushadi.
set -euo pipefail
cd "$(dirname "$0")"
MODE="${1:-prod}"

need() { command -v "$1" >/dev/null 2>&1 || { echo "❌ $1 topilmadi. Oʻrnating: $2"; exit 1; }; }
need python3 "https://www.python.org/downloads/ yoki: brew install python"
need node "https://nodejs.org/ yoki: brew install node"

[ -f .env ] || { cp .env.example .env; echo "ℹ️  .env yaratildi. Kalitlarni (ANTHROPIC_API_KEY, ASL_BELGISI_API_KEY) shu faylga yozing."; }

if [ "$MODE" = "mobile" ]; then
  need npm "Node.js bilan birga keladi"
  cd mobile
  if [ ! -d node_modules ] || [ package.json -nt node_modules/.installed ]; then
    echo "📦 Mobil ilova paketlari oʻrnatilmoqda…"
    npm install --no-audit --no-fund && touch node_modules/.installed
  fi
  echo "📱 iPhone: App Store dan 'Expo Go' ni oʻrnating, keyin quyidagi QR ni iPhone Kamerasi bilan skanerlang."
  echo "   Ilovada Sozlamalar → './start.sh public' bergan https manzilni yozing."
  exec npx expo start
fi

env_get() { grep -E "^$1=" .env 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '"' || true; }
BOT_TOKEN="$(env_get TELEGRAM_BOT_TOKEN)"

bot_deps() {
  if [ ! -f backend/.venv/.bot-installed ] || [ bot/requirements.txt -nt backend/.venv/.bot-installed ]; then
    echo "📦 Telegram bot paketlari oʻrnatilmoqda…"
    backend/.venv/bin/pip install -q -r bot/requirements.txt && touch backend/.venv/.bot-installed
  fi
}

if [ "$MODE" = "bot" ]; then
  [ -n "$BOT_TOKEN" ] || { echo "❌ .env ga TELEGRAM_BOT_TOKEN yozing (@BotFather → /newbot)."; exit 1; }
  [ -x backend/.venv/bin/python ] || { echo "❌ Avval ./start.sh ni bir marta ishga tushiring."; exit 1; }
  bot_deps
  cd bot && exec env TELEGRAM_BOT_TOKEN="$BOT_TOKEN" API_URL="${API_URL:-http://127.0.0.1:8000}" \
    WEB_URL="${WEB_URL:-}" ../backend/.venv/bin/python bot.py
fi

if [ "$MODE" = "reset" ]; then
  rm -f backend/doriishonch.db && echo "🗑  Demo baza oʻchirildi. Keyingi ishga tushirishda qayta yaratiladi."
  exit 0
fi

# --- Backend paketlari
if [ ! -x backend/.venv/bin/uvicorn ] || [ backend/requirements.txt -nt backend/.venv/.installed ]; then
  echo "📦 Python paketlari oʻrnatilmoqda…"
  python3 -m venv backend/.venv
  backend/.venv/bin/pip install -q --upgrade pip
  backend/.venv/bin/pip install -q -r backend/requirements.txt
  touch backend/.venv/.installed
fi

if [ "$MODE" = "test" ]; then
  (cd backend && .venv/bin/python -m pytest -q)
  echo "— Telegram bot testlari —"
  cd bot && exec ../backend/.venv/bin/python -m pytest -q tests
fi

# --- Frontend paketlari
if [ ! -d frontend/node_modules ] || [ frontend/package.json -nt frontend/node_modules/.installed ]; then
  echo "📦 Frontend paketlari oʻrnatilmoqda…"
  (cd frontend && npm install --no-audit --no-fund && touch node_modules/.installed)
fi

if [ "$MODE" != "dev" ]; then
  # Kod oʻzgargan boʻlsa, qayta yigʻamiz
  if [ ! -f frontend/.next/BUILD_ID ] || [ -n "$(find frontend/app frontend/components frontend/lib frontend/next.config.ts -newer frontend/.next/BUILD_ID 2>/dev/null | head -1)" ]; then
    echo "🔨 Frontend yigʻilmoqda (1-2 daqiqa)…"
    (cd frontend && npm run build >/dev/null)
  fi
fi

# Oldingi ishga tushirishdan qolgan DoriIshonch serverlari portni band qilgan boʻlsa, ularni toʻxtatamiz
free_port() {
  local port=$1 pid cmd
  for pid in $(lsof -ti tcp:"$port" -sTCP:LISTEN 2>/dev/null || true); do
    cmd="$(ps -o command= -p "$pid" 2>/dev/null || true)"
    if echo "$cmd" | grep -Eq "uvicorn app.main|next-server|next start|next dev|expo start|@expo/cli|expo/bin/cli"; then
      echo "♻️  $port-portdagi eski server toʻxtatildi (pid $pid)"
      kill "$pid" 2>/dev/null || true
    else
      echo "❌ $port-port boshqa dastur bilan band: $cmd"; exit 1
    fi
  done
}
if [ "$MODE" != "bot" ]; then
  free_port 8000; free_port 3000
  [ "$MODE" = "iphone" ] || [ "$MODE" = "mobile" ] && free_port 8081
  # Oldingi demo tunnelini yopamiz (faqat bizning .tools/cloudflared)
  pkill -f "$PWD/.tools/cloudflared tunnel" 2>/dev/null || true
  sleep 1
fi

PIDS=()
cleanup() { echo; echo "⏹  Toʻxtatilmoqda…"; for p in "${PIDS[@]:-}"; do kill "$p" 2>/dev/null || true; done; }
trap cleanup EXIT INT TERM

if [ "$MODE" = "dev" ]; then
  (cd backend && exec .venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000) & PIDS+=($!)
  sleep 2
  (cd frontend && exec npm run dev -- --port 3000 --hostname 0.0.0.0) & PIDS+=($!)
else
  (cd backend && exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000) & PIDS+=($!)
  sleep 2
  (cd frontend && exec npx next start --port 3000 --hostname 0.0.0.0) & PIDS+=($!)
fi

# Backend tayyor boʻlguncha kutamiz (birinchi marta demo baza yaratiladi)
for _ in $(seq 1 60); do curl -s http://127.0.0.1:8000/health >/dev/null 2>&1 && break; sleep 1; done

LAN_IP="$( (ipconfig getifaddr en0 || ipconfig getifaddr en1 || hostname -I | awk '{print $1}') 2>/dev/null | head -1 || true)"
echo
echo "✅ DoriIshonch ishga tushdi"
echo "   Kompyuterda:        http://localhost:3000"
[ -n "$LAN_IP" ] && echo "   Shu Wi-Fi dagi telefon: http://$LAN_IP:3000  (kamera bu manzilda ishlamaydi: ./start.sh public)"
echo "   API hujjatlari:     http://localhost:8000/docs"

ensure_cloudflared() {
  if command -v cloudflared >/dev/null 2>&1; then CF="$(command -v cloudflared)"; return; fi
  CF="$PWD/.tools/cloudflared"
  [ -x "$CF" ] && return
  echo "📦 cloudflared yuklab olinmoqda (bir marta, ~20 MB)…"
  mkdir -p .tools
  local arch; arch="$(uname -m)"; [ "$arch" = "x86_64" ] && arch=amd64; [ "$arch" = "aarch64" ] && arch=arm64
  local os; os="$(uname -s | tr '[:upper:]' '[:lower:]')"
  if [ "$os" = "darwin" ]; then
    curl -fsSL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-$arch.tgz" | tar -xz -C .tools
  else
    curl -fsSL -o "$CF" "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-$arch"
  fi
  chmod +x "$CF"
}

URL=""
if [ "$MODE" = "public" ] || [ "$MODE" = "iphone" ]; then
  if ensure_cloudflared; then
    echo "🌍 HTTPS manzil tayyorlanmoqda…"
    LOG="$(mktemp)"
    "$CF" tunnel --no-autoupdate --url http://localhost:3000 >"$LOG" 2>&1 & PIDS+=($!)
    for _ in $(seq 1 40); do
      URL="$(grep -Eo 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG" | head -1 || true)"
      [ -n "$URL" ] && break; sleep 1
    done
  fi
  if [ -n "$URL" ]; then
    echo "   📱 Sayt (kamera ishlaydi, istalgan telefondan): $URL"
    echo "      Demo kodlar: $URL/demo-kodlar"
  else
    echo "   ⚠️  HTTPS tunnel ochilmadi. Telefon uchun: http://$LAN_IP:3000 (bu manzilda sayt kamerasi ishlamaydi)"
  fi
fi

if [ -n "$BOT_TOKEN" ] && [ "$MODE" != "test" ]; then
  bot_deps
  (cd bot && exec env TELEGRAM_BOT_TOKEN="$BOT_TOKEN" API_URL=http://127.0.0.1:8000 WEB_URL="${URL:-}" \
    ../backend/.venv/bin/python bot.py) & PIDS+=($!)
  echo "   🤖 Telegram bot ishga tushdi${URL:+ (Mini App: $URL)}"
fi
echo
if [ "$MODE" = "iphone" ]; then
  API="${URL:-http://$LAN_IP:3000}"
  printf "SAYT: %s\nLAN: http://%s:3000\nILOVA_SERVER: %s\n" "${URL:-yoʻq}" "$LAN_IP" "$API" > DEMO-URL.txt
  printf "EXPO_PUBLIC_API_URL=%s\n" "$API" > mobile/.env
  if [ -n "$URL" ]; then
    echo; echo "   🔳 Saytni iPhone da ochish uchun QR (iPhone Kamerasi bilan skanerlang):"
    npx --yes qrcode-terminal "$URL" 2>/dev/null || true
  fi
  cd mobile
  if [ ! -x node_modules/.bin/expo ] || [ ! -f node_modules/.installed ] || [ package.json -nt node_modules/.installed ]; then
    echo "📦 Mobil ilova paketlari oʻrnatilmoqda (birinchi marta bir necha daqiqa; sayt shu vaqtda ham ishlaydi)…"
    for try in 1 2 3 4; do
      if npm install --no-audit --no-fund --fetch-timeout=600000 --fetch-retries=6 --fetch-retry-mintimeout=20000; then
        touch node_modules/.installed; break
      fi
      echo "↻ Internet sekin: qayta urinish ($try/4)…"; sleep 5
    done
  fi
  if [ ! -x node_modules/.bin/expo ]; then
    echo "⚠️  Ilova paketlari oʻrnatilmadi (internet juda sekin). Sayt ishlashda davom etadi: ${URL:-http://localhost:3000}"
    echo "   Keyinroq qayta urinib koʻring: DEMO.command ni yana oching."
    wait
  fi
  echo
  echo "📱 iPhone ILOVA: App Store dan 'Expo Go' ni oʻrnating. Pastdagi QR ni iPhone Kamerasi bilan skanerlang."
  echo "   Ilova serverga avtomatik ulanadi: $API"
  echo "   (iPhone va kompyuter bitta Wi-Fi/hotspot da boʻlishi kerak)"
  ./node_modules/.bin/expo start --lan || wait
  exit 0
fi

echo "   Toʻxtatish: Ctrl+C"
wait
