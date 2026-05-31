#!/usr/bin/env bash
# Panel overlay seçici — COMPOSE_FILE değerini stdout veya .env.compose dosyasına yazar.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PANEL="${1:-}"

usage() {
  cat <<'EOF'
Kullanım: ./deploy/panel-compose.sh <panel> [--write]

  panel   coolify | dokploy | 1panel | portainer | plesk | vps | none
  --write .env.compose dosyasına yazar (docker compose otomatik okur)

Örnek:
  export COMPOSE_FILE=$(./deploy/panel-compose.sh dokploy)
  docker compose up -d --build
EOF
}

write_file=0
if [[ "${2:-}" == "--write" ]]; then
  write_file=1
fi

case "$PANEL" in
  coolify)
    CF="docker-compose.yaml:deploy/coolify/docker-compose.coolify.yaml"
    ;;
  dokploy)
    CF="docker-compose.yaml:deploy/dokploy/docker-compose.dokploy.yaml"
    ;;
  1panel)
    CF="docker-compose.yaml:deploy/1panel/docker-compose.1panel.yaml"
    ;;
  portainer)
    CF="docker-compose.yaml:deploy/portainer/docker-compose.portainer.yaml"
    ;;
  plesk)
    CF="docker-compose.yaml:deploy/plesk/docker-compose.plesk.yaml"
    ;;
  vps)
    CF="docker-compose.yaml:deploy/docker-compose.vps.yaml"
    ;;
  none|'')
    CF="docker-compose.yaml"
    ;;
  -h|--help)
    usage
    exit 0
    ;;
  *)
    echo "Bilinmeyen panel: $PANEL" >&2
    usage
    exit 1
    ;;
esac

if [[ "$write_file" -eq 1 ]]; then
  printf 'COMPOSE_FILE=%s\n' "$CF" > "$ROOT/.env.compose"
  echo "Yazıldı: $ROOT/.env.compose"
  echo "COMPOSE_FILE=$CF"
else
  echo "$CF"
fi
