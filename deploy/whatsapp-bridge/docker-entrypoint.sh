#!/usr/bin/env sh
set -eu

SECRETS_DIR="${COOLOPS_SECRETS_DIR:-${KOBIOPS_SECRETS_DIR:-/run/kobiops-secrets}}"
TOKEN_FILE="${SECRETS_DIR}/whatsapp_bridge_token"

if [ -z "${WHATSAPP_BRIDGE_TOKEN:-}" ] && [ -f "$TOKEN_FILE" ]; then
  WHATSAPP_BRIDGE_TOKEN="$(tr -d '\r\n' < "$TOKEN_FILE")"
  export WHATSAPP_BRIDGE_TOKEN
fi

exec node server.js
