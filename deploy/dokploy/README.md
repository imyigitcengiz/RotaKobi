# CoolOPS — Dokploy kurulumu (tak-çalıştır)

[Dokploy](https://dokploy.com) ile Docker Compose modunda panel + WhatsApp köprüsü birlikte çalışır.

## 3 adımda deploy

1. **Project** → **Docker Compose** → **Create**
2. **Source:** GitHub → `imyigitcengiz/cool-ops`, branch `main`  
   **Compose file path:** `docker-compose.yaml`
3. **Environment** → [dokploy.env.example](./dokploy.env.example) dosyasını açıp içeriği yapıştırın  
   (minimal sürüm: [dokploy.env.minimal](./dokploy.env.minimal))  
   **`APP_URL`** satırını kendi domain'inizle değiştirin (`/` olmadan, sslip.io için `http://`).
4. **Domains** → servis **`app`** (whatsapp_bridge değil), container port **`80`**, HTTPS **kapalı** (sslip.io)  
   → **Deploy** (domain değiştirdikten sonra mutlaka yeniden deploy)

**Env şablonları**

| Dosya | Ne için |
|-------|---------|
| [dokploy.env.example](./dokploy.env.example) | Dokploy UI'ya yapıştır — açıklamalı tam şablon |
| [dokploy.env.minimal](./dokploy.env.minimal) | Sadece 5 satır, hızlı başlangıç |
| [../../.env.example](../../.env.example) | Tüm değişkenler referansı (Coolify, VPS, override) |

Repo kökünde `.env` oluşturmanız **gerekmez** — Dokploy Environment sekmesi yeterli.  
Secret, ALLOWED_HOSTS ve CSRF → `bootstrap-env.sh` otomatik doldurur.

- URL (sslip.io): `http://glgede-yaam-coolops-....sslip.io/giris/` (**https değil**)
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

Dokploy domain birincil URL için (gelecek sürümler / manuel):

```env
APP_URL=https://panel.sizin-domain.com
```

`bootstrap-env.sh` bunu CSRF için kullanır.

## GitHub otomatik deploy

Dokploy → **Deployments** → **Webhook** → GitHub push event.

## Sorun giderme

| Belirti | Çözüm |
|---------|--------|
| **404 page not found** | Domain servisi **`app`**, port **80**. sslip.io → **http://** (https değil). Overlay'de `traefik.docker.network=dokploy-network` olmalı — redeploy. Dokploy → **Reload Traefik**. Log: `daphne 0.0.0.0:80` |
| **Deploy error / Restarting** | Logs → app konteyneri. `KRİTİK: /data` → volume bağlı mı? Eski stack `kobi-ops` çalışıyorsa durdurun. |
| DisallowedHost | `APP_URL=http://tam-domain.sslip.io` (slash yok) + redeploy |
| 404 / sslip | `DJANGO_SECURE_SSL` otomatik 0; http:// kullanın |
| CSRF | Domain ile CSRF otomatik; redeploy |
| Port 80 meşgul | Dokploy overlay kullanın; host ports kapatın |
| WhatsApp kapalı | `whatsapp_bridge` logs; RAM kontrol |
| Veri sıfırlandı | `kobiops_gy_data` volume koruyun |

Tüm paneller: [deploy/README.md](../README.md) · Genel: [DEPLOY.md](../../DEPLOY.md)
