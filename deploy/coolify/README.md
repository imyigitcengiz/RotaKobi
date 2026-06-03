# Coolify kurulumu (Ghost tarzı — kutudan çıkar çıkmaz)

Otomatik domain: [DOMAIN.md](../DOMAIN.md) · Env: [coolify.env.example](coolify.env.example)

## ÖNEMLİ: `:8000` tarayıcıda Coolify panelidir

| Adres | Ne açılır |
|-------|-----------|
| `http://SUNUCU-IP:8000` | **Coolify yönetim paneli** |
| Generate Domain URL | **KobiOps uygulaması** (Traefik üzerinden) |

Tarayıcıda **asla `:8000` yazmayın** — sunucunun 8000 portu Coolify'a aittir.

## Build Pack

| Ayar | Değer |
|------|--------|
| Build Pack | **Docker Compose** |
| Compose path | `docker-compose.yaml` |
| Domain servisi | **`app`** |
| Container port | **80** |
| Environment | **Boş bırakın** (veya [coolify.env.example](coolify.env.example)) |

**APP_URL, DJANGO_ALLOWED_HOSTS, sslip.io domain — elle yazmayın.** Coolify **Generate Domain** ile otomatik üretir.

Tüm paneller: [deploy/README.md](../README.md)

## Domain (otomatik)

1. Coolify → servis **`app`** → **Generate Domain**
2. Port **80** → **Save** → **Deploy**
3. Tarayıcıda Coolify'ın ürettiği URL'yi açın (**`:8000` ekleme**)

Kendi domain'inizi bağlarsanız Coolify yine `SERVICE_FQDN_APP` / `SERVICE_URL_APP` enjekte eder — Environment'a bir şey yazmanız gerekmez.

Eski kurulumda Environment'ta `APP_URL=http://....sslip.io` varsa **silin** ve redeploy yapın.

`whatsapp_bridge` servisine domain **bağlamayın**.

## Log kontrolü

Deploy sonrası Logs'ta:
```text
[cool-ops] ALLOWED_HOSTS ← SERVICE_FQDN_APP: ...
daphne 0.0.0.0:80
```

## Exited / volume

Build Pack Dockerfile ise volume bağlanmaz → Compose'a geçin.

Genel: [DEPLOY.md](../../DEPLOY.md)
