# CoolOPS — panel & VPS kurulum uyumluluğu

Tek `docker-compose.yaml`; platforma göre **overlay** dosyası eklenir (`COMPOSE_FILE`).

## Hızlı seçim

| Platform | Compose overlay | Rehber |
|----------|-----------------|--------|
| **Coolify** | *(gerekmez)* veya `deploy/coolify/docker-compose.coolify.yaml` | [coolify/README.md](coolify/README.md) |
| **Dokploy** | `deploy/dokploy/docker-compose.dokploy.yaml` | [dokploy/README.md](dokploy/README.md) |
| **1Panel** | `deploy/1panel/docker-compose.1panel.yaml` | [1panel/README.md](1panel/README.md) |
| **Portainer** | `deploy/portainer/docker-compose.portainer.yaml` | [portainer/README.md](portainer/README.md) |
| **Easypanel** | *(gerekmez)* | [easypanel/README.md](easypanel/README.md) |
| **Plesk Git** | `deploy/plesk/docker-compose.plesk.yaml` | [plesk/README.md](plesk/README.md) |
| **VPS / SSH** | `deploy/docker-compose.vps.yaml` | `./deploy/install.sh` |

## COMPOSE_FILE örnekleri

```bash
# VPS (varsayılan install.sh)
export COMPOSE_FILE=docker-compose.yaml:deploy/docker-compose.vps.yaml

# Dokploy
export COMPOSE_FILE=docker-compose.yaml:deploy/dokploy/docker-compose.dokploy.yaml

# 1Panel
export COMPOSE_FILE=docker-compose.yaml:deploy/1panel/docker-compose.1panel.yaml

# Portainer Stack ortam değişkeni
COMPOSE_FILE=docker-compose.yaml:deploy/portainer/docker-compose.portainer.yaml
```

Veya: `./deploy/panel-compose.sh dokploy` → `.env.compose` yazar.

## Ortak kurallar (tüm paneller)

1. **Build pack:** Docker Compose — yalnızca Dockerfile değil.
2. **Compose path:** repo kökü `docker-compose.yaml`.
3. **Domain servisi:** `app` (whatsapp_bridge'e domain bağlamayın).
4. **Container port:** `80` (Dokploy domain UI, Coolify Generate Domain).
5. **Volume:** `kobiops_gy_data` → `/data` — deploy sırasında silmeyin.
6. **RAM:** ≥ 2 GB (WhatsApp köprüsü + Chromium).
7. **`.env` zorunlu değil** — `deploy/bootstrap-env.sh` secret, ALLOWED_HOSTS, CSRF doldurur.

## Otomatik ortam algılama

`bootstrap-env.sh` ve `common/panel_env.py` şu değişkenleri okur:

| Kaynak | Değişkenler |
|--------|-------------|
| Coolify | `SERVICE_FQDN_APP`, `SERVICE_URL_APP`, `COOLIFY_FQDN` |
| Dokploy | `DOKPLOY_DEPLOY_URL`, `DOKPLOY_FQDN`, `DOKPLOY_URL`, `APP_URL` |
| Genel | `DOMAIN`, `APP_DOMAIN`, `HOSTNAME`, `WEBSITE_URL` |

## Tek komut (VPS)

```bash
git clone https://github.com/imyigitcengiz/cool-ops.git /opt/cool-ops
cd /opt/cool-ops
./deploy/install.sh panel.firma.com
# veya panel profili:
./deploy/install.sh panel.firma.com --panel dokploy
```

Detaylı üretim: [DEPLOY.md](../DEPLOY.md)
