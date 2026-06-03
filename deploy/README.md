# CoolOPS — panel & VPS kurulum uyumluluğu

Tek `docker-compose.yaml`; platforma göre **overlay** dosyası eklenir (`COMPOSE_FILE`).

**Otomatik domain (tüm paneller):** [DOMAIN.md](DOMAIN.md) · Ortak env başlığı: [panel.env.template](panel.env.template)

## Hızlı seçim

| Platform | Compose overlay | Env şablonu | Rehber |
|----------|-----------------|-------------|--------|
| **Coolify** | isteğe bağlı `deploy/coolify/...` | [coolify/coolify.env.example](coolify/coolify.env.example) | [coolify/README.md](coolify/README.md) |
| **Dokploy** | `deploy/dokploy/docker-compose.dokploy.yaml` | [dokploy/dokploy.env.minimal](dokploy/dokploy.env.minimal) | [dokploy/README.md](dokploy/README.md) |
| **1Panel** | `deploy/1panel/docker-compose.1panel.yaml` | [1panel/1panel.env.example](1panel/1panel.env.example) | [1panel/README.md](1panel/README.md) |
| **Plesk Git** | `deploy/plesk/docker-compose.plesk.yaml` | [plesk/plesk.env.example](plesk/plesk.env.example) | [plesk/README.md](plesk/README.md) |
| **Plesk Stacks** | `deploy/plesk/docker-compose.plesk-stack.yaml` | [plesk/plesk-stack.env.example](plesk/plesk-stack.env.example) | [plesk/README.md](plesk/README.md) |
| **Portainer** | `deploy/portainer/docker-compose.portainer.yaml` | [panel.env.template](panel.env.template) | [portainer/README.md](portainer/README.md) |
| **Easypanel** | *(gerekmez)* | [panel.env.template](panel.env.template) | [easypanel/README.md](easypanel/README.md) |
| **VPS / SSH** | `deploy/docker-compose.vps.yaml` | `./deploy/install.sh domain` | `./deploy/install.sh` |

## Ortak kurallar (tüm paneller)

1. **Build pack:** Docker Compose — yalnızca Dockerfile değil.
2. **Compose path:** repo kökü `docker-compose.yaml`.
3. **Domain servisi:** `app` (`whatsapp_bridge`'e domain bağlamayın).
4. **Container port:** `80`.
5. **Domain elle yazmayın:** `APP_URL`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`.
6. **Volume:** `kobiops_gy_data` → `/data` — deploy sırasında silmeyin.
7. **`.env` zorunlu değil** — `panel-domain.sh` + `bootstrap-env.sh` otomatik doldurur.

## COMPOSE_FILE örnekleri

```bash
# Dokploy
export COMPOSE_FILE=docker-compose.yaml:deploy/dokploy/docker-compose.dokploy.yaml

# 1Panel
export COMPOSE_FILE=docker-compose.yaml:deploy/1panel/docker-compose.1panel.yaml

# Plesk Git (deploy.sh otomatik ayarlar)
COMPOSE_FILE=docker-compose.yaml:deploy/plesk/docker-compose.plesk.yaml

# VPS
export COMPOSE_FILE=docker-compose.yaml:deploy/docker-compose.vps.yaml
```

`./deploy/panel-compose.sh dokploy` → `.env.compose` yazar.

## Tek komut (VPS)

```bash
git clone https://github.com/imyigitcengiz/cool-ops.git /opt/cool-ops
cd /opt/cool-ops
./deploy/install.sh panel.firma.com
```

Detaylı üretim: [DEPLOY.md](../DEPLOY.md)
