#!/usr/bin/env bash
# Git pull + docker compose rebuild (1Panel / VPS; Dokploy kendi webhook'unu kullanır)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
git fetch origin main
git reset --hard origin/main
docker compose up -d --build
echo "$(date -Is) sync OK"
