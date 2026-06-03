# CoolOPS — Otomatik domain (tüm paneller)

Tek `docker-compose.yaml` + panel overlay. Domain **elle yazılmaz** — panel enjekte eder veya `KOBIOPS_DOMAIN` ile verilir; `deploy/panel-domain.sh` Django ayarlarını üretir.

## Ortak kural

| Elle yazmayın | Otomatik üretilir |
|---------------|-------------------|
| `APP_URL` | `SERVICE_URL_APP` |
| `DJANGO_ALLOWED_HOSTS` | `SERVICE_FQDN_APP` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | bootstrap + `panel-domain.sh` |
| `DJANGO_SECRET_KEY` | `/data/.django_secret_key` |

**Env şablonu (ortak başlık):** [panel.env.template](panel.env.template)

## Panel karşılaştırması

| Panel | Domain nasıl gelir | Env şablonu | Compose overlay |
|-------|-------------------|-------------|-----------------|
| **Coolify** | UI → servis `app` → **Generate Domain** → `SERVICE_FQDN_APP` | [coolify/coolify.env.example](coolify/coolify.env.example) | isteğe bağlı [coolify/docker-compose.coolify.yaml](coolify/docker-compose.coolify.yaml) |
| **Dokploy** | UI → **Domains** → servis `app`, port **80** → `SERVICE_*` | [dokploy/dokploy.env.minimal](dokploy/dokploy.env.minimal) | [dokploy/docker-compose.dokploy.yaml](dokploy/docker-compose.dokploy.yaml) |
| **Plesk Git** | `deploy.sh` vhost yolundan veya `KOBIOPS_DOMAIN` → `SERVICE_*` | [plesk/plesk.env.example](plesk/plesk.env.example) | [plesk/docker-compose.plesk.yaml](plesk/docker-compose.plesk.yaml) |
| **Plesk Stacks** | Stack env: `KOBIOPS_DOMAIN` | [plesk/plesk-stack.env.example](plesk/plesk-stack.env.example) | [plesk/docker-compose.plesk-stack.yaml](plesk/docker-compose.plesk-stack.yaml) |
| **1Panel** | Reverse proxy domain → stack env `KOBIOPS_DOMAIN` | [1panel/1panel.env.example](1panel/1panel.env.example) | [1panel/docker-compose.1panel.yaml](1panel/docker-compose.1panel.yaml) |
| **VPS / SSH** | `./deploy/install.sh panel.firma.com` → `KOBIOPS_DOMAIN` | — | [docker-compose.vps.yaml](docker-compose.vps.yaml) |

## Canonical değişkenler

Tüm paneller container içinde şu değerlere normalize edilir:

```text
SERVICE_FQDN_APP=panel.ornek.com
SERVICE_URL_APP=https://panel.ornek.com   # sslip.io → http://
```

Kaynak eşlemesi (`deploy/panel-domain.sh` = `common/panel_env.py`):

| Panel değişkeni | → Canonical |
|-----------------|-------------|
| Coolify/Dokploy `SERVICE_FQDN_APP` | doğrudan |
| `KOBIOPS_DOMAIN` (Plesk, 1Panel, VPS) | `SERVICE_FQDN_APP` |
| `KOBIOPS_PUBLIC_URL` | `SERVICE_URL_APP` |
| `DOKPLOY_FQDN` / `DOMAIN` | yedek FQDN |

## sslip.io / traefik.me

Coolify **Generate Domain** sslip üretirse:

- `SERVICE_URL_APP` → `http://...`
- `DJANGO_SECURE_SSL=0` (http→https redirect kapalı)
- `DJANGO_ALLOW_SSLIP_HOSTS=1` (otomatik)

Kendi domain + HTTPS (Plesk, 1Panel reverse proxy):

- `SERVICE_URL_APP` → `https://...`
- `DJANGO_SECURE_SSL=1`

## Log kontrolü

Deploy sonrası app logları:

```text
[cool-ops] ALLOWED_HOSTS ← panel.ornek.com
[cool-ops] CSRF ← https://panel.ornek.com
[cool-ops] Panel URL: https://panel.ornek.com/
```

## Sorun giderme

| Belirti | Çözüm |
|---------|--------|
| Eski sslip.io / DisallowedHost | Environment'tan `APP_URL`, `DJANGO_ALLOWED_HOSTS` sil → redeploy |
| CSRF hatası | Domain panelde `app` servisine bağlı mı? Plesk/1Panel: `KOBIOPS_DOMAIN` doğru mu? |
| 404 (Traefik) | Coolify/Dokploy: servis `app`, port **80**; `whatsapp_bridge`'e domain bağlamayın |

Kod: [panel-domain.sh](panel-domain.sh) · [common/panel_env.py](../common/panel_env.py)
