#!/usr/bin/env bash
# Plesk Git → "Additional deployment actions" veya manuel: bash deploy/plesk/deploy.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT"

LOG_DIR="$ROOT/deploy/plesk/logs"
LOG_FILE="$LOG_DIR/deploy.log"
mkdir -p "$LOG_DIR"

exec >> >(tee -a "$LOG_FILE") 2>&1

echo "=== KobiOps Plesk deploy $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
echo "ROOT=$ROOT"

# --- Ortam ---
PLESK_ENV="$SCRIPT_DIR/plesk.env"
if [[ -f "$PLESK_ENV" ]]; then
  # shellcheck disable=SC1090
  source "$PLESK_ENV"
fi

_detect_domain_from_path() {
  local path="$ROOT"
  if [[ "$path" =~ /vhosts/[^/]+/([^/]+)/?$ ]]; then
    echo "${BASH_REMATCH[1]}"
    return 0
  fi
  if [[ "$path" =~ /subdomains/([^/]+)/ ]]; then
    echo "${BASH_REMATCH[1]}"
    return 0
  fi
  return 1
}

if [[ -z "${KOBIOPS_DOMAIN:-}" ]]; then
  KOBIOPS_DOMAIN="$(_detect_domain_from_path 2>/dev/null || true)"
fi

if [[ -z "${KOBIOPS_DOMAIN:-}" ]]; then
  echo "HATA: KOBIOPS_DOMAIN tanımlı değil."
  echo "  cp deploy/plesk/plesk.env.example deploy/plesk/plesk.env"
  echo "  KOBIOPS_DOMAIN=ops.ornek.com yazın"
  exit 1
fi

KOBIOPS_HTTP_PORT="${KOBIOPS_HTTP_PORT:-8080}"
export KOBIOPS_DOMAIN KOBIOPS_HTTP_PORT

if [[ -z "${KOBIOPS_PUBLIC_URL:-}" ]]; then
  if [[ "$KOBIOPS_DOMAIN" == *".sslip.io"* ]]; then
    KOBIOPS_PUBLIC_URL="http://${KOBIOPS_DOMAIN}"
  else
    KOBIOPS_PUBLIC_URL="https://${KOBIOPS_DOMAIN}"
  fi
fi
export KOBIOPS_PUBLIC_URL

export COMPOSE_FILE="$ROOT/docker-compose.yaml:$SCRIPT_DIR/docker-compose.plesk.yaml"
export KOBIOPS_PLESK=1

# --- Ön kontroller ---
if ! command -v docker >/dev/null 2>&1; then
  echo "HATA: Docker yüklü değil. SSH: curl -fsSL https://get.docker.com | sh"
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "HATA: docker compose plugin gerekli."
  exit 1
fi

# Plesk Git bazen root olmayan kullanıcıyla çalışır — docker grubu
if ! docker info >/dev/null 2>&1; then
  echo "HATA: docker komutu çalışmıyor (izin?). Kullanıcıyı docker grubuna ekleyin veya script'i root ile çalıştırın."
  exit 1
fi

# --- .env (ilk kurulum) ---
if [[ ! -f "$ROOT/.env" ]]; then
  echo "İlk kurulum: .env oluşturuluyor..."
  DOMAIN="$KOBIOPS_DOMAIN" DJANGO_ENSURE_SUPERADMIN="${DJANGO_ENSURE_SUPERADMIN:-1}" \
    "$ROOT/deploy/install.sh" --force
else
  echo "Güncelleme: docker compose build + up..."
  docker compose up -d --build --remove-orphans
fi

# --- Sağlık ---
echo "Konteyner durumu:"
docker compose ps

HEALTH_URL="http://127.0.0.1:${KOBIOPS_HTTP_PORT}/healthz/"
echo "Healthcheck: $HEALTH_URL"
for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -fsS --max-time 5 "$HEALTH_URL" >/dev/null 2>&1; then
    echo "OK — uygulama ayakta."
    echo "Panel: ${KOBIOPS_PUBLIC_URL}/giris/"
    echo "=== Deploy bitti ==="
    exit 0
  fi
  echo "  bekleniyor ($i/10)..."
  sleep 6
done

echo "UYARI: healthz yanıt vermedi — log: docker compose logs app --tail 80"
docker compose logs app --tail 40 || true
exit 1
