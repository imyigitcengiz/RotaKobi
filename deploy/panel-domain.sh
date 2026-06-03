#!/usr/bin/env bash
# Ortak panel domain otomatik algılama — Coolify, Dokploy, Plesk, 1Panel, VPS
# Kaynak: deploy/bootstrap-env.sh (container entrypoint)
set -euo pipefail

# shellcheck disable=SC2034
PANEL_DOMAIN_FQDN_KEYS=(
  SERVICE_FQDN_APP SERVICE_FQDN
  KOBIOPS_DOMAIN PLESK_DOMAIN DOKPLOY_FQDN
  DOMAIN APP_DOMAIN HOSTNAME COOLIFY_FQDN
)
PANEL_DOMAIN_URL_KEYS=(
  SERVICE_URL_APP SERVICE_URL
  KOBIOPS_PUBLIC_URL DOKPLOY_DEPLOY_URL DOKPLOY_URL WEBSITE_URL
)

panel_domain_strip_host() {
  local raw="${1:-}"
  raw="${raw#https://}"
  raw="${raw#http://}"
  raw="${raw%%/*}"
  raw="${raw%%:*}"
  echo "$raw"
}

panel_domain_is_http_only() {
  case "$1" in
    *.sslip.io|*.traefik.me) return 0 ;;
    *) return 1 ;;
  esac
}

panel_domain_read_fqdn_key() {
  local key="$1"
  local val="${!key:-}"
  if [[ -n "$val" ]]; then
    panel_domain_strip_host "$val"
    return 0
  fi
  return 1
}

panel_domain_detect_fqdn() {
  local key fqdn=""
  for key in "${PANEL_DOMAIN_FQDN_KEYS[@]}"; do
    fqdn="$(panel_domain_read_fqdn_key "$key" 2>/dev/null || true)"
    if [[ -n "$fqdn" ]]; then
      echo "$fqdn"
      return 0
    fi
  done
  for key in "${PANEL_DOMAIN_URL_KEYS[@]}" APP_URL; do
    local url="${!key:-}"
    if [[ -n "$url" ]]; then
      panel_domain_strip_host "$url"
      return 0
    fi
  done
  return 1
}

panel_domain_origin_from_fqdn() {
  local fqdn="$1"
  if panel_domain_is_http_only "$fqdn"; then
    echo "http://${fqdn}"
  else
    echo "https://${fqdn}"
  fi
}

panel_domain_normalize() {
  # Tüm paneller → tek SERVICE_FQDN_APP / SERVICE_URL_APP (Django + bootstrap)
  if [[ -z "${SERVICE_FQDN_APP:-}" ]]; then
    local fqdn=""
    fqdn="$(panel_domain_detect_fqdn 2>/dev/null || true)"
    if [[ -n "$fqdn" ]]; then
      export SERVICE_FQDN_APP="$fqdn"
    fi
  else
    export SERVICE_FQDN_APP="$(panel_domain_strip_host "$SERVICE_FQDN_APP")"
  fi

  if [[ -z "${SERVICE_URL_APP:-}" ]]; then
    local url="" key
    for key in SERVICE_URL KOBIOPS_PUBLIC_URL DOKPLOY_DEPLOY_URL DOKPLOY_URL WEBSITE_URL; do
      url="${!key:-}"
      if [[ -n "$url" ]]; then
        url="${url%/}"
        if [[ "$url" != http://* && "$url" != https://* ]]; then
          url="$(panel_domain_origin_from_fqdn "$(panel_domain_strip_host "$url")")"
        fi
        export SERVICE_URL_APP="$url"
        break
      fi
    done
    if [[ -n "${SERVICE_FQDN_APP:-}" ]]; then
      export SERVICE_URL_APP="$(panel_domain_origin_from_fqdn "$SERVICE_FQDN_APP")"
    elif [[ -n "${APP_URL:-}" && -z "${SERVICE_FQDN_APP:-}" ]]; then
      export SERVICE_URL_APP="${APP_URL%/}"
      local _legacy_host
      _legacy_host="$(panel_domain_strip_host "$APP_URL")"
      if [[ -n "$_legacy_host" ]]; then
        export SERVICE_FQDN_APP="$_legacy_host"
      fi
    fi
  else
    export SERVICE_URL_APP="${SERVICE_URL_APP%/}"
    if [[ "$SERVICE_URL_APP" != http://* && "$SERVICE_URL_APP" != https://* ]]; then
      export SERVICE_URL_APP="$(panel_domain_origin_from_fqdn "$(panel_domain_strip_host "$SERVICE_URL_APP")")"
    fi
    if [[ -z "${SERVICE_FQDN_APP:-}" ]]; then
      export SERVICE_FQDN_APP="$(panel_domain_strip_host "$SERVICE_URL_APP")"
    fi
  fi
}

panel_domain_warn_legacy() {
  if [[ -n "${APP_URL:-}" && -n "${SERVICE_FQDN_APP:-}" ]]; then
    local _app_host
    _app_host="$(panel_domain_strip_host "$APP_URL")"
    if [[ "$_app_host" != "$SERVICE_FQDN_APP" ]]; then
      echo "[cool-ops] UYARI: APP_URL (${_app_host}) yok sayılıyor — SERVICE_FQDN_APP=${SERVICE_FQDN_APP}"
      echo "[cool-ops]          Panel Environment'tan APP_URL / DJANGO_ALLOWED_HOSTS / DJANGO_CSRF_TRUSTED_ORIGINS silin."
    fi
  fi
  if [[ -n "${DJANGO_ALLOWED_HOSTS:-}" && -n "${SERVICE_FQDN_APP:-}" ]]; then
    if [[ "${DJANGO_ALLOWED_HOSTS}" != *"${SERVICE_FQDN_APP}"* ]]; then
      echo "[cool-ops] UYARI: DJANGO_ALLOWED_HOSTS elle ayarlı — SERVICE_FQDN_APP=${SERVICE_FQDN_APP} ile güncelleniyor."
    fi
  fi
}

panel_domain_detect_ip() {
  local ip=""
  if command -v hostname >/dev/null 2>&1; then
    ip="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
  fi
  if [[ -z "$ip" ]] && command -v ip >/dev/null 2>&1; then
    ip="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for (i=1;i<=NF;i++) if ($i=="src") print $(i+1)}' || true)"
  fi
  echo "${ip:-127.0.0.1}"
}

panel_domain_apply_django() {
  local _ip _app_port _csrf_base _fqdn _url
  _ip="$(panel_domain_detect_ip)"
  _app_port="${PORT:-80}"
  _csrf_base="http://127.0.0.1:${_app_port},http://localhost:${_app_port},http://${_ip}:${_app_port}"

  if [[ -n "${SERVICE_FQDN_APP:-}" ]]; then
    export DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1,${_ip},${SERVICE_FQDN_APP}"
    echo "[cool-ops] ALLOWED_HOSTS ← ${SERVICE_FQDN_APP}"
  elif [[ -z "${DJANGO_ALLOWED_HOSTS:-}" ]]; then
    _fqdn="$(panel_domain_detect_fqdn 2>/dev/null || true)"
    if [[ -n "$_fqdn" ]]; then
      export DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1,${_ip},${_fqdn}"
      echo "[cool-ops] ALLOWED_HOSTS otomatik: ${_fqdn}"
    else
      export DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1,${_ip}"
      echo "[cool-ops] ALLOWED_HOSTS otomatik (IP): ${_ip}"
    fi
  fi

  if [[ -n "${SERVICE_URL_APP:-}" ]]; then
    _url="${SERVICE_URL_APP%/}"
    export DJANGO_CSRF_TRUSTED_ORIGINS="${_csrf_base},${_url}"
    if [[ "$_url" == https://* ]]; then
      export DJANGO_SECURE_SSL="${DJANGO_SECURE_SSL:-1}"
    elif [[ -z "${DJANGO_SECURE_SSL:-}" ]]; then
      export DJANGO_SECURE_SSL=0
    fi
    echo "[cool-ops] CSRF ← ${_url}"
  elif [[ -z "${DJANGO_CSRF_TRUSTED_ORIGINS:-}" ]]; then
    _fqdn="$(panel_domain_detect_fqdn 2>/dev/null || true)"
    if [[ -n "$_fqdn" ]]; then
      if panel_domain_is_http_only "$_fqdn"; then
        export DJANGO_CSRF_TRUSTED_ORIGINS="${_csrf_base},http://${_fqdn}"
        export DJANGO_SECURE_SSL="${DJANGO_SECURE_SSL:-0}"
      else
        export DJANGO_CSRF_TRUSTED_ORIGINS="${_csrf_base},https://${_fqdn}"
        export DJANGO_SECURE_SSL="${DJANGO_SECURE_SSL:-1}"
      fi
      echo "[cool-ops] CSRF otomatik (FQDN): ${_fqdn}"
    fi
  fi

  if [[ -n "${DJANGO_ALLOWED_HOSTS:-}" ]]; then
    if [[ "${DJANGO_ALLOWED_HOSTS}" == *".sslip.io"* || "${DJANGO_ALLOWED_HOSTS}" == *".traefik.me"* ]]; then
      export DJANGO_SECURE_SSL=0
    fi
  fi

  _fqdn="${SERVICE_FQDN_APP:-$(panel_domain_detect_fqdn 2>/dev/null || true)}"
  if [[ -n "$_fqdn" ]] && panel_domain_is_http_only "$_fqdn"; then
    export DJANGO_ALLOW_SSLIP_HOSTS="${DJANGO_ALLOW_SSLIP_HOSTS:-1}"
  else
    export DJANGO_ALLOW_SSLIP_HOSTS="${DJANGO_ALLOW_SSLIP_HOSTS:-0}"
  fi
}

panel_domain_log_url() {
  if [[ -n "${SERVICE_URL_APP:-}" ]]; then
    echo "[cool-ops] Panel URL: ${SERVICE_URL_APP%/}/"
  elif [[ -n "${SERVICE_FQDN_APP:-}" ]]; then
    echo "[cool-ops] Panel URL: $(panel_domain_origin_from_fqdn "$SERVICE_FQDN_APP")/"
  fi
}
