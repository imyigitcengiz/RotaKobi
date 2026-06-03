#!/usr/bin/env bash
# Coolify / Dokploy / Plesk / 1Panel — ortam değişkenlerini otomatik tamamlar.
# docker-entrypoint.sh kaynaklar; elle .env yazmadan deploy mümkün.
set -euo pipefail

_BOOTSTRAP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=panel-domain.sh
source "$_BOOTSTRAP_DIR/panel-domain.sh"

# Eski KOBIOPS_* env (geriye dönük uyumluluk)
_legacy_env() {
  local new_name=$1 old_name=$2
  if [[ -z "${!new_name:-}" && -n "${!old_name:-}" ]]; then
    export "${new_name}=${!old_name}"
  fi
}
_legacy_env COOLOPS_COMPOSE_STACK KOBIOPS_COMPOSE_STACK
_legacy_env COOLOPS_SECRETS_DIR KOBIOPS_SECRETS_DIR
_legacy_env COOLOPS_BUILD_COMMIT KOBIOPS_BUILD_COMMIT
_legacy_env COOLOPS_UPDATE_REPO KOBIOPS_UPDATE_REPO
_legacy_env COOLOPS_UPDATE_BRANCH KOBIOPS_UPDATE_BRANCH
_legacy_env COOLOPS_DEPLOY_WEBHOOK_URL KOBIOPS_DEPLOY_WEBHOOK_URL
_legacy_env COOLOPS_HTTP_PORT KOBIOPS_HTTP_PORT

_data_dir="${DATA_DIR:-/data}"
export DATA_DIR="$_data_dir"
mkdir -p "$_data_dir" 2>/dev/null || true

_gen_secret() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -base64 48 | tr -d '\n/+=' | head -c 64
  elif command -v python3 >/dev/null 2>&1; then
    python3 -c "import secrets; print(secrets.token_urlsafe(48))"
  else
    date +%s | sha256sum | head -c 64
  fi
}

# --- SECRET KEY (kalıcı: /data/.django_secret_key) ---
_secret_file="${_data_dir}/.django_secret_key"
if [[ -z "${DJANGO_SECRET_KEY:-}" ]]; then
  if [[ -f "$_secret_file" ]]; then
    DJANGO_SECRET_KEY="$(tr -d '\r\n' < "$_secret_file")"
    export DJANGO_SECRET_KEY
  elif [[ -n "${SERVICE_PASSWORD_APP:-}" ]]; then
    export DJANGO_SECRET_KEY="${SERVICE_PASSWORD_APP}"
    printf '%s' "$DJANGO_SECRET_KEY" > "$_secret_file"
    chmod 600 "$_secret_file" 2>/dev/null || true
  elif [[ -n "${SERVICE_REALBASE64_APP:-}" ]]; then
    export DJANGO_SECRET_KEY="${SERVICE_REALBASE64_APP}"
    printf '%s' "$DJANGO_SECRET_KEY" > "$_secret_file"
    chmod 600 "$_secret_file" 2>/dev/null || true
  else
    DJANGO_SECRET_KEY="$(_gen_secret)"
    export DJANGO_SECRET_KEY
    if mkdir -p "$_data_dir" 2>/dev/null; then
      printf '%s' "$DJANGO_SECRET_KEY" > "$_secret_file"
      chmod 600 "$_secret_file" 2>/dev/null || true
      echo "[cool-ops] DJANGO_SECRET_KEY otomatik üretildi → ${_secret_file}"
    else
      echo "[cool-ops] UYARI: /data yazılamıyor — secret kalıcı kaydedilemedi."
    fi
  fi
fi

# --- Panel domain (Coolify / Dokploy / Plesk / 1Panel / VPS) ---
panel_domain_normalize
panel_domain_warn_legacy
panel_domain_apply_django

# İlk kurulum: süper admin yoksa oluşturulur (admin/admin). Şifre sıfırlama: DJANGO_ENSURE_SUPERADMIN_RESET=1
# İsteğe bağlı özel şifre: DJANGO_SUPERADMIN_PASSWORD=...
export DJANGO_ENSURE_SUPERADMIN="${DJANGO_ENSURE_SUPERADMIN:-0}"

# WhatsApp köprü Bearer token (paylaşımlı volume: kobiops_secrets)
_secrets_dir="${COOLOPS_SECRETS_DIR:-${KOBIOPS_SECRETS_DIR:-/run/kobiops-secrets}}"
export COOLOPS_SECRETS_DIR="$_secrets_dir"
mkdir -p "$_secrets_dir" 2>/dev/null || true
_bridge_token_file="${_secrets_dir}/whatsapp_bridge_token"
if [[ -z "${WHATSAPP_BRIDGE_TOKEN:-}" ]]; then
  if [[ -f "$_bridge_token_file" ]]; then
    WHATSAPP_BRIDGE_TOKEN="$(tr -d '\r\n' < "$_bridge_token_file")"
    export WHATSAPP_BRIDGE_TOKEN
  else
    WHATSAPP_BRIDGE_TOKEN="$(_gen_secret)"
    export WHATSAPP_BRIDGE_TOKEN
    if mkdir -p "$_secrets_dir" 2>/dev/null; then
      printf '%s' "$WHATSAPP_BRIDGE_TOKEN" > "$_bridge_token_file"
      chmod 600 "$_bridge_token_file" 2>/dev/null || true
      chmod 700 "$_secrets_dir" 2>/dev/null || true
      echo "[cool-ops] WHATSAPP_BRIDGE_TOKEN otomatik üretildi → ${_bridge_token_file}"
    else
      echo "[cool-ops] UYARI: köprü token kalıcı kaydedilemedi (${_secrets_dir})."
    fi
  fi
fi

# WhatsApp köprü varsayılanları
if [[ "${COOLOPS_COMPOSE_STACK:-${KOBIOPS_COMPOSE_STACK:-0}}" == "1" ]]; then
  export WHATSAPP_BRIDGE_URL="${WHATSAPP_BRIDGE_URL:-http://whatsapp_bridge:3939}"
  export DJANGO_WHATSAPP_BRIDGE_WAIT_ON_START="${DJANGO_WHATSAPP_BRIDGE_WAIT_ON_START:-0}"
else
  # Tek konteyner (Dockerfile / Nixpacks) — ayrı köprü servisi yok
  export WHATSAPP_BRIDGE_URL="${WHATSAPP_BRIDGE_URL:-}"
  export DJANGO_WHATSAPP_BRIDGE_WAIT_ON_START="${DJANGO_WHATSAPP_BRIDGE_WAIT_ON_START:-0}"
fi
export DJANGO_WHATSAPP_BRIDGE_CAN_SPAWN="${DJANGO_WHATSAPP_BRIDGE_CAN_SPAWN:-0}"
export DJANGO_WHATSAPP_BRIDGE_AUTO_START="${DJANGO_WHATSAPP_BRIDGE_AUTO_START:-0}"

export DATA_DIR="${DATA_DIR:-/data}"
export DJANGO_DB_PATH="${DJANGO_DB_PATH:-${DATA_DIR}/db.sqlite3}"
export DJANGO_MEDIA_ROOT="${DJANGO_MEDIA_ROOT:-${DATA_DIR}/media}"
export DJANGO_SERVE_MEDIA="${DJANGO_SERVE_MEDIA:-1}"
export GY_REQUIRE_PERSISTENT_VOLUME="${GY_REQUIRE_PERSISTENT_VOLUME:-1}"
export DJANGO_DEBUG="${DJANGO_DEBUG:-0}"

panel_domain_log_url