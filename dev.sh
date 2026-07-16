#!/usr/bin/env bash
#
# Levanta toda la app TacticEYE con un único comando: migraciones + API +
# webhook listener de Stripe (si hay clave configurada) + frontend Next.js.
#
# Uso: ./dev.sh
# Parar: Ctrl+C (detiene los tres procesos limpiamente)
#
set -uo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(cd "$REPO_DIR/../tacticeye-web" 2>/dev/null && pwd || true)"
LOG_DIR="$REPO_DIR/runtime_data/dev_logs"
mkdir -p "$LOG_DIR"
cd "$REPO_DIR"

# Cargar variables de entorno del backend (.env), si existe
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

# La Stripe CLI se suele instalar en ~/.local/bin
export PATH="$HOME/.local/bin:$PATH"

PORT="${PORT:-8000}"
PIDS=()
CLEANED=0

cleanup() {
  [ "$CLEANED" = 1 ] && return
  CLEANED=1
  echo ""
  echo "Deteniendo servicios..."
  for pid in "${PIDS[@]:-}"; do
    [ -z "$pid" ] && continue
    # Grupo (setsid: uvicorn/stripe/frontend) + PID directo (p.ej. tail,
    # que no crea grupo propio) — enviar ambos es inofensivo si ya murió.
    kill -TERM "-$pid" 2>/dev/null
    kill -TERM "$pid" 2>/dev/null
  done
  sleep 1
  for pid in "${PIDS[@]:-}"; do
    [ -z "$pid" ] && continue
    kill -KILL "-$pid" 2>/dev/null
    kill -KILL "$pid" 2>/dev/null
  done
  echo "Todo detenido."
}
trap cleanup EXIT INT TERM

start_bg() {
  local name="$1" logfile="$2"; shift 2
  echo "→ Iniciando $name..."
  setsid "$@" > "$logfile" 2>&1 < /dev/null &
  PIDS+=("$!")
}

echo "→ Aplicando migraciones..."
alembic upgrade head

start_bg "API (puerto $PORT)" "$LOG_DIR/api.log" \
  uvicorn app_service.main:app --port "$PORT"

if [ -n "${STRIPE_SECRET_KEY:-}" ] && command -v stripe >/dev/null 2>&1; then
  start_bg "Stripe webhook listener" "$LOG_DIR/stripe.log" \
    stripe listen --api-key "$STRIPE_SECRET_KEY" --forward-to "localhost:$PORT/billing/webhook"
else
  echo "⚠ Stripe listen omitido (sin STRIPE_SECRET_KEY en .env o CLI no instalada)"
  echo "  La app funciona igual con el plan Free; los pagos no sincronizarán en local."
fi

if [ -n "$FRONTEND_DIR" ] && [ -d "$FRONTEND_DIR" ]; then
  if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "→ Instalando dependencias del frontend (primera vez, puede tardar)..."
    (cd "$FRONTEND_DIR" && npm install)
  fi
  # OJO: no heredar la variable PORT del backend (viene de .env) — next dev
  # también la respeta y se quedaría con el puerto de la API en vez del 3000.
  start_bg "Frontend (puerto 3000)" "$LOG_DIR/web.log" \
    env -u PORT bash -c "cd '$FRONTEND_DIR' && exec npm run dev"
else
  echo "⚠ No se encontró tacticeye-web en $REPO_DIR/../tacticeye-web — solo se levanta la API"
fi

echo -n "Esperando a que la API esté lista"
for _ in $(seq 1 30); do
  if curl -s "http://localhost:$PORT/health" 2>/dev/null | grep -q ok; then
    echo " ✓"
    break
  fi
  echo -n "."
  sleep 1
done

echo ""
echo "======================================================"
echo " TacticEYE en marcha"
echo "   API:      http://localhost:$PORT"
echo "   Frontend: http://localhost:3000"
echo "   Logs:     $LOG_DIR/{api,stripe,web}.log"
echo "   Ctrl+C para detener todo"
echo "======================================================"
echo ""

# Importante: NO ejecutar tail -f en primer plano de forma directa. Bash
# no atiende los traps (Ctrl+C) hasta que un comando en primer plano
# termina por sí solo; en segundo plano + `wait` sí se interrumpe al
# instante en cuanto llega la señal.
tail -f "$LOG_DIR"/*.log &
TAIL_PID=$!
PIDS+=("$TAIL_PID")
wait "$TAIL_PID"
