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

# Dokploy bazen konteyner ID'sini (5bffcfbd178d) SERVICE_FQDN_APP olarak enjekte eder
panel_domain_is_plausible_fqdn() {
  local h="${1:-}"
  [[ -z "$h" ]] && return 1
  case "$h" in
    localhost|127.0.0.1|'[::1]') return 0 ;;
  esac
  [[ "$h" == *.* ]] || return 1
  return 0
}

# Dokploy çoklu domain: host1.sslip.io,ops.example.com
panel_domain_split_csv_hosts() {
  local raw="${1:-}"
  local part host
  PANEL_FQDN_HOSTS=()
  [[ -z "$raw" ]] && return 0
  IFS=',' read -r -a _parts <<< "$raw"
  for part in "${_parts[@]}"; do
    part="$(echo "$part" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    host="$(panel_domain_strip_host "$part")"
    if [[ -n "$host" ]] && panel_domain_is_plausible_fqdn "$host"; then
      PANEL_FQDN_HOSTS+=("$host")
    fi
  done
}

panel_domain_split_csv_urls() {
  local raw="${1:-}"
  local part url host
  PANEL_SERVICE_URLS=()
  [[ -z "$raw" ]] && return 0
  IFS=',' read -r -a _parts <<< "$raw"
  for part in "${_parts[@]}"; do
    part="$(echo "$part" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    [[ -z "$part" ]] && continue
    url="${part%/}"
    if [[ "$url" != http://* && "$url" != https://* ]]; then
      host="$(panel_domain_strip_host "$url")"
      url="$(panel_domain_origin_from_fqdn "$host")"
    fi
    host="$(panel_domain_strip_host "$url")"
    if [[ -n "$host" ]] && panel_domain_is_http_only "$host"; then
      url="http://${host}"
    fi
    PANEL_SERVICE_URLS+=("$url")
  done
}

panel_domain_pick_primary_fqdn() {
  local host
  for host in "${PANEL_FQDN_HOSTS[@]}"; do
    if ! panel_domain_is_http_only "$host"; then
      echo "$host"
      return 0
    fi
  done
  if [[ ${#PANEL_FQDN_HOSTS[@]} -gt 0 ]]; then
    echo "${PANEL_FQDN_HOSTS[0]}"
  fi
}

panel_domain_join_csv() {
  local IFS=','
  echo "$*"
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

panel_domain_is_self_hosted() {
  case "${COOLOPS_PANEL:-}" in
    plesk|1panel|vps) return 0 ;;
  esac
  [[ "${KOBIOPS_PLESK:-}" == "1" ]] && return 0
  return 1
}

panel_domain_normalize_kobiops_host() {
  # Plesk / 1Panel / VPS — KOBIOPS_DOMAIN birincil; Coolify/Dokploy kalıntıları yok sayılır
  local fqdn url
  fqdn="$(panel_domain_strip_host "${KOBIOPS_DOMAIN:-${PLESK_DOMAIN:-}}")"
  if [[ -z "$fqdn" ]]; then
    fqdn="$(panel_domain_strip_host "${DOMAIN:-}")"
  fi
  if [[ -z "$fqdn" ]]; then
    echo "[cool-ops] HATA: KOBIOPS_DOMAIN tanımlı değil (Plesk/1Panel)."
    return 1
  fi
  export SERVICE_FQDN_APP="$fqdn"
  url="${KOBIOPS_PUBLIC_URL:-}"
  url="${url%/}"
  if [[ -n "$url" ]]; then
    if [[ "$url" != http://* && "$url" != https://* ]]; then
      url="$(panel_domain_origin_from_fqdn "$(panel_domain_strip_host "$url")")"
    fi
    export SERVICE_URL_APP="$url"
  else
    export SERVICE_URL_APP="$(panel_domain_origin_from_fqdn "$fqdn")"
  fi
  export DJANGO_ALLOW_SSLIP_HOSTS=0
}

panel_domain_normalize() {
  if panel_domain_is_self_hosted; then
    panel_domain_normalize_kobiops_host
    return 0
  fi

  # Coolify/Dokploy → Plesk geçişi: .env'deki eski sslip SERVICE_FQDN yok say
  if [[ -n "${KOBIOPS_DOMAIN:-}" && -n "${SERVICE_FQDN_APP:-}" ]]; then
    local _svc _kobi
    _svc="$(panel_domain_strip_host "$SERVICE_FQDN_APP")"
    _kobi="$(panel_domain_strip_host "$KOBIOPS_DOMAIN")"
    if [[ "$_svc" != "$_kobi" ]] && panel_domain_is_http_only "$_svc"; then
      echo "[cool-ops] UYARI: Eski sslip domain (${_svc}) yok sayılıyor → KOBIOPS_DOMAIN=${_kobi}"
      unset SERVICE_FQDN_APP SERVICE_URL_APP APP_URL
    fi
  fi

  # Tüm paneller → SERVICE_FQDN_APP / SERVICE_URL_APP (Dokploy: virgülle çoklu domain)
  PANEL_FQDN_HOSTS=()
  PANEL_SERVICE_URLS=()
  if [[ -n "${SERVICE_FQDN_APP:-}" ]]; then
    if [[ "${SERVICE_FQDN_APP}" == *","* ]]; then
      panel_domain_split_csv_hosts "$SERVICE_FQDN_APP"
    else
      panel_domain_split_csv_hosts "$(panel_domain_strip_host "$SERVICE_FQDN_APP")"
    fi
    if [[ ${#PANEL_FQDN_HOSTS[@]} -eq 0 ]]; then
      echo "[cool-ops] UYARI: Geçersiz SERVICE_FQDN_APP (${SERVICE_FQDN_APP}) — konteyner adı yok sayılıyor."
      unset SERVICE_FQDN_APP
    else
      export SERVICE_FQDN_APP="$(panel_domain_pick_primary_fqdn)"
      export PANEL_FQDN_LIST="$(panel_domain_join_csv "${PANEL_FQDN_HOSTS[@]}")"
    fi
  fi
  if [[ -z "${SERVICE_FQDN_APP:-}" ]]; then
    local fqdn=""
    fqdn="$(panel_domain_detect_fqdn 2>/dev/null || true)"
    if [[ -n "$fqdn" ]] && panel_domain_is_plausible_fqdn "$fqdn"; then
      export SERVICE_FQDN_APP="$fqdn"
      PANEL_FQDN_HOSTS=("$fqdn")
      export PANEL_FQDN_LIST="$fqdn"
    fi
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
    if [[ "${SERVICE_URL_APP}" == *","* ]]; then
      panel_domain_split_csv_urls "$SERVICE_URL_APP"
      if [[ ${#PANEL_SERVICE_URLS[@]} -gt 0 ]]; then
        export SERVICE_URL_APP="${PANEL_SERVICE_URLS[0]}"
        export PANEL_URL_LIST="$(panel_domain_join_csv "${PANEL_SERVICE_URLS[@]}")"
      fi
    else
      export SERVICE_URL_APP="${SERVICE_URL_APP%/}"
      if [[ "$SERVICE_URL_APP" != http://* && "$SERVICE_URL_APP" != https://* ]]; then
        export SERVICE_URL_APP="$(panel_domain_origin_from_fqdn "$(panel_domain_strip_host "$SERVICE_URL_APP")")"
      fi
      _url_host="$(panel_domain_strip_host "$SERVICE_URL_APP")"
      if [[ -n "$_url_host" ]] && panel_domain_is_http_only "$_url_host"; then
        export SERVICE_URL_APP="http://${_url_host}"
      fi
      PANEL_SERVICE_URLS=("$SERVICE_URL_APP")
      export PANEL_URL_LIST="$SERVICE_URL_APP"
    fi
    if [[ -z "${SERVICE_FQDN_APP:-}" ]] && [[ ${#PANEL_SERVICE_URLS[@]} -gt 0 ]]; then
      PANEL_FQDN_HOSTS=()
      for u in "${PANEL_SERVICE_URLS[@]}"; do
        h="$(panel_domain_strip_host "$u")"
        if [[ -n "$h" ]] && panel_domain_is_plausible_fqdn "$h"; then
          PANEL_FQDN_HOSTS+=("$h")
        fi
      done
      if [[ ${#PANEL_FQDN_HOSTS[@]} -gt 0 ]]; then
        export SERVICE_FQDN_APP="$(panel_domain_pick_primary_fqdn)"
        export PANEL_FQDN_LIST="$(panel_domain_join_csv "${PANEL_FQDN_HOSTS[@]}")"
      fi
    fi
  fi

  if [[ -n "${PANEL_FQDN_LIST:-}" && ${#PANEL_FQDN_HOSTS[@]} -eq 0 ]]; then
    panel_domain_split_csv_hosts "$PANEL_FQDN_LIST"
  fi
  if [[ -n "${PANEL_URL_LIST:-}" && ${#PANEL_SERVICE_URLS[@]} -eq 0 ]]; then
    panel_domain_split_csv_urls "$PANEL_URL_LIST"
  fi

  # URL'lerdeki hostları FQDN listesine ekle (çoklu Dokploy domain)
  if [[ ${#PANEL_SERVICE_URLS[@]} -gt 0 ]]; then
    for u in "${PANEL_SERVICE_URLS[@]}"; do
      h="$(panel_domain_strip_host "$u")"
      if [[ -n "$h" ]] && panel_domain_is_plausible_fqdn "$h"; then
        local found=0
        for existing in "${PANEL_FQDN_HOSTS[@]}"; do
          if [[ "$existing" == "$h" ]]; then found=1; break; fi
        done
        if [[ $found -eq 0 ]]; then
          PANEL_FQDN_HOSTS+=("$h")
        fi
      fi
    done
    if [[ ${#PANEL_FQDN_HOSTS[@]} -gt 0 ]]; then
      export PANEL_FQDN_LIST="$(panel_domain_join_csv "${PANEL_FQDN_HOSTS[@]}")"
      if [[ -z "${SERVICE_FQDN_APP:-}" ]]; then
        export SERVICE_FQDN_APP="$(panel_domain_pick_primary_fqdn)"
      fi
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
  local _ip _app_port _csrf_base _fqdn _url _host _hosts _csrf _has_sslip _has_https
  _ip="$(panel_domain_detect_ip)"
  _app_port="${PORT:-80}"
  _csrf_base="http://127.0.0.1:${_app_port},http://localhost:${_app_port},http://${_ip}:${_app_port}"

  _hosts="localhost,127.0.0.1,${_ip}"
  if [[ ${#PANEL_FQDN_HOSTS[@]} -gt 0 ]]; then
    for _host in "${PANEL_FQDN_HOSTS[@]}"; do
      if [[ "${_hosts}" != *"${_host}"* ]]; then
        _hosts="${_hosts},${_host}"
      fi
    done
    export DJANGO_ALLOWED_HOSTS="${_hosts}"
    echo "[cool-ops] ALLOWED_HOSTS ← $(panel_domain_join_csv "${PANEL_FQDN_HOSTS[@]}")"
  elif [[ -n "${SERVICE_FQDN_APP:-}" ]]; then
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

  _csrf="${_csrf_base}"
  _has_sslip=0
  _has_https=0
  if [[ ${#PANEL_SERVICE_URLS[@]} -gt 0 ]]; then
    for _url in "${PANEL_SERVICE_URLS[@]}"; do
      _url="${_url%/}"
      _url_host="$(panel_domain_strip_host "$_url")"
      if [[ -n "$_url_host" ]] && panel_domain_is_http_only "$_url_host"; then
        _url="http://${_url_host}"
        _has_sslip=1
      elif [[ "$_url" == https://* ]]; then
        _has_https=1
      fi
      if [[ "${_csrf}" != *"${_url}"* ]]; then
        _csrf="${_csrf},${_url}"
      fi
    done
    export SERVICE_URL_APP="${PANEL_SERVICE_URLS[0]}"
    export DJANGO_CSRF_TRUSTED_ORIGINS="${_csrf}"
    echo "[cool-ops] CSRF ← $(panel_domain_join_csv "${PANEL_SERVICE_URLS[@]}")"
    if [[ $_has_https -eq 1 ]]; then
      export DJANGO_SECURE_SSL="${DJANGO_SECURE_SSL:-1}"
    fi
    if [[ $_has_sslip -eq 1 ]]; then
      export DJANGO_ALLOW_SSLIP_HOSTS="${DJANGO_ALLOW_SSLIP_HOSTS:-1}"
      if [[ $_has_https -eq 0 ]]; then
        export DJANGO_SECURE_SSL="${DJANGO_SECURE_SSL:-0}"
      fi
    fi
  elif [[ -n "${SERVICE_URL_APP:-}" ]]; then
    _url="${SERVICE_URL_APP%/}"
    _url_host="$(panel_domain_strip_host "$_url")"
    # Dokploy bazen sslip.io için https:// enjekte eder — HTTP'ye normalize et
    if [[ -n "$_url_host" ]] && panel_domain_is_http_only "$_url_host"; then
      _url="http://${_url_host}"
      export SERVICE_URL_APP="$_url"
      if [[ -z "${SERVICE_FQDN_APP:-}" ]]; then
        export SERVICE_FQDN_APP="$_url_host"
      fi
      if [[ -z "${DJANGO_ALLOWED_HOSTS:-}" ]] || [[ "${DJANGO_ALLOWED_HOSTS}" != *"${_url_host}"* ]]; then
        export DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1,${_ip},${_url_host}"
        echo "[cool-ops] ALLOWED_HOSTS ← ${_url_host} (sslip URL)"
      fi
      export DJANGO_SECURE_SSL=0
    elif [[ "$_url" == https://* ]]; then
      export DJANGO_SECURE_SSL="${DJANGO_SECURE_SSL:-1}"
    elif [[ -z "${DJANGO_SECURE_SSL:-}" ]]; then
      export DJANGO_SECURE_SSL=0
    fi
    export DJANGO_CSRF_TRUSTED_ORIGINS="${_csrf_base},${_url}"
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
