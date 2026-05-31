# KobiOps — Dokploy kurulumu (tak-çalıştır)

[Dokploy](https://dokploy.com) ile Docker Compose modunda panel + WhatsApp köprüsü birlikte çalışır.

## 3 adımda deploy

1. **Project** → **Docker Compose** → **Create**
2. **Source:** GitHub → `imyigitcengiz/kobi-ops`, branch `main`  
   **Compose file path:** `docker-compose.yaml`
3. **Environment** (isteğe bağlı, önerilir):
   ```env
   COMPOSE_FILE=docker-compose.yaml:deploy/dokploy/docker-compose.dokploy.yaml
   ```
4. **Domains** → servis **`app`**, container port **`80`**, HTTPS açık/kapalı  
   → **Deploy**

`.env` yazmanız **gerekmez** — `bootstrap-env.sh` secret, host ve CSRF'yi otomatik tamamlar.

- URL: `https://panel.sizin-domain.com/giris/`
- İlk giriş: **admin** / **admin**
- Sonra `DJANGO_ENSURE_SUPERADMIN=0` + redeploy

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

Manuel override: [`.env.example`](../../.env.example)

Dokploy UI değişkenleri `.env` dosyasına yazılır; compose `env_file: .env` ile okur.

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
| App Restarting / SECRET_KEY | Logs; `/data` volume var mı? Redeploy |
| DisallowedHost | Domain `app` servisine bağlı mı? `APP_URL` veya Domains |
| 404 / sslip | `DJANGO_SECURE_SSL` otomatik 0; http:// kullanın |
| CSRF | Domain ile CSRF otomatik; redeploy |
| Port 80 meşgul | Dokploy overlay kullanın; host ports kapatın |
| WhatsApp kapalı | `whatsapp_bridge` logs; RAM kontrol |
| Veri sıfırlandı | `kobiops_gy_data` volume koruyun |

Tüm paneller: [deploy/README.md](../README.md) · Genel: [DEPLOY.md](../../DEPLOY.md)
