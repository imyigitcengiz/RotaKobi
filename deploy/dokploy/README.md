# CoolOPS — Dokploy kurulumu (tak-çalıştır)

Otomatik domain: [DOMAIN.md](../DOMAIN.md) · Env: [dokploy.env.minimal](dokploy.env.minimal)

[Dokploy](https://dokploy.com) ile Docker Compose modunda panel + WhatsApp köprüsü birlikte çalışır.

## 3 adımda deploy

### A) Git + Compose (önerilen)

1. **Project** → **Docker Compose** → **Create**
2. **Source:** GitHub → `imyigitcengiz/cool-ops`, branch `main`  
   **Compose file path:** `docker-compose.yaml`
3. **Environment** → [dokploy.env.minimal](./dokploy.env.minimal) (APP_URL yazmayın)
4. **Domains** → servis **`app`**, port **`80`** → **Deploy** (domain otomatik enjekte edilir)

Overlay için env: `COMPOSE_FILE=docker-compose.yaml:deploy/dokploy/docker-compose.dokploy.yaml`

### B) Compose Raw (tek dosya — Dockerfile modu işe yaramadıysa)

1. **Docker Compose** → **Compose Type: Raw**
2. Repo’daki **[docker-compose.raw.yaml](./docker-compose.raw.yaml)** içeriğini yapıştır  
   veya Git path: `deploy/dokploy/docker-compose.raw.yaml`
3. **Environment:**
   ```env
   DJANGO_ENSURE_SUPERADMIN=1
   DJANGO_DEBUG=0
   ```
4. **Domains** → **`app`**, port **80** → **Deploy**

Raw dosya: `app` + `whatsapp_bridge` + `dokploy-network` + volume’ler — overlay gerekmez.

**Env şablonları**

| Dosya | Ne için |
|-------|---------|
| [dokploy.env.example](./dokploy.env.example) | Dokploy UI'ya yapıştır — açıklamalı tam şablon |
| [dokploy.env.minimal](./dokploy.env.minimal) | Hızlı başlangıç (domain otomatik) |
| [../../.env.example](../../.env.example) | Tüm değişkenler referansı (Coolify, VPS, override) |

Repo kökünde `.env` oluşturmanız **gerekmez** — Dokploy Environment sekmesi yeterli.  
Secret, ALLOWED_HOSTS ve CSRF → `bootstrap-env.sh` + Dokploy domain enjekte eder (`SERVICE_FQDN_APP`).

- Panel URL: Dokploy **Domains** sekmesindeki adres + `/giris/`
- İlk giriş: **admin** / **admin**
- Şifre sıfırlama (tek redeploy): `DJANGO_ENSURE_SUPERADMIN_RESET=1` → sonra `0`
- Mevcut kurulumda şifre bilinmiyorsa: app konteynerinde `cat /data/.initial_admin_password`

## Ön koşullar

- En az **2 GB RAM** (WhatsApp köprüsü Chromium kullanır)
- DNS A kaydı → sunucu IP
- Dokploy **Domains** sekmesi: host port açmayın; Traefik yönlendirir

## Overlay ne işe yarar?

`deploy/dokploy/docker-compose.dokploy.yaml`:

- Host `ports` bağlamaz (80 çakışması önlenir)
- `dokploy-network` (Traefik) ile `app` servisini birleştirir

Overlay olmadan da çalışabilir; domain tanımlıysa ana compose yeterlidir.

## Kalıcı veri

Named volume **`kobiops_gy_data`** → `/data` (SQLite + medya). Deploy sırasında volume silmeyin.

## Environment (isteğe bağlı)

Dokploy şablonu: **[deploy/dokploy/dokploy.env.example](dokploy/dokploy.env.example)**  
Genel referans: [`.env.example`](../.env.example)

`DJANGO_SECRET_KEY` içinde `$` varsa tek tırnak: `DJANGO_SECRET_KEY='abc$xyz'`

Domain tanımlayınca Dokploy `SERVICE_FQDN_APP` / `SERVICE_URL_APP` gönderir — **APP_URL yazmayın**.

## GitHub otomatik deploy

Dokploy → **Deployments** → **Webhook** → GitHub push event.

## Sorun giderme

| Belirti | Çözüm |
|---------|--------|
| **404 page not found** | Domain servisi **`app`**, port **80**. sslip.io → **http://** (https değil). Overlay'de `traefik.docker.network=dokploy-network` olmalı — redeploy. Dokploy → **Reload Traefik**. Log: `daphne 0.0.0.0:80` |
| **Deploy error / Restarting** | Logs → app konteyneri. `KRİTİK: /data` → volume bağlı mı? Eski stack `kobi-ops` çalışıyorsa durdurun. |
| DisallowedHost | Environment'tan eski `APP_URL` / `DJANGO_ALLOWED_HOSTS` satırlarını silin → redeploy |
| 404 / sslip | `DJANGO_SECURE_SSL` otomatik 0; http:// kullanın |
| CSRF | Domain ile CSRF otomatik; redeploy |
| Port 80 meşgul | Dokploy overlay kullanın; host ports kapatın |
| WhatsApp kapalı | `whatsapp_bridge` logs; RAM kontrol |
| Veri sıfırlandı | `kobiops_gy_data` volume koruyun |

Tüm paneller: [deploy/README.md](../README.md) · Genel: [DEPLOY.md](../../DEPLOY.md)
