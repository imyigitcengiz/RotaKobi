# CoolOPS — Dokploy kurulumu

[Dokploy](https://dokploy.com) ile tam uyumlu Docker Compose deploy.

## Hızlı kurulum (önerilen)

### 1. Proje oluştur

| Alan | Değer |
|------|--------|
| Tip | **Docker Compose** |
| Repo | `https://github.com/imyigitcengiz/RotaKobi` |
| Branch | `main` |
| Compose path | `docker-compose.yaml` |

### 2. Environment

[`dokploy.env.minimal`](dokploy.env.minimal) dosyasını yapıştırın:

```env
COMPOSE_FILE=docker-compose.yaml:deploy/dokploy/docker-compose.dokploy.yaml
DJANGO_ENSURE_SUPERADMIN=1
DJANGO_DEBUG=0
```

**Yazmayın:** `DATABASE_URL`, `REDIS_URL`, `SERVICE_FQDN_APP`, `SERVICE_URL_APP`, `DJANGO_ALLOWED_HOSTS`, `APP_URL`

Bunlar otomatik ayarlanır (`bootstrap-env.sh` + Dokploy Domains).

### 3. Domains

Her domain **ayrı satır** olarak ekleyin:

| Servis | Port | Protokol |
|--------|------|----------|
| `app` | **80** | sslip.io → **HTTP** |
| `app` | **80** | ops.firma.com → **HTTPS** |

- Servis adı mutlaka **`app`** (whatsapp_bridge değil)
- Container port **80** (8000 değil)
- Virgülle birleştirilmiş domain **Environment'a yazmayın**

### 4. Deploy

Deploy sonrası logda şunları görmelisiniz:

```text
[cool-ops] PostgreSQL hazır.
[cool-ops] ALLOWED_HOSTS ← ops.firma.com, xxx.sslip.io
[cool-ops] CSRF ← https://ops.firma.com,http://xxx.sslip.io
[cool-ops] daphne 0.0.0.0:80
```

**4 konteyner** çalışmalı: `app`, `db`, `redis`, `whatsapp_bridge`

Giriş: `https://ops.firma.com/giris/` — `admin` / `admin` (hemen değiştirin)

---

## Compose Raw (alternatif)

Overlay kullanmak istemezseniz:

- Compose path: `deploy/dokploy/docker-compose.raw.yaml`
- Environment: yalnızca `DJANGO_ENSURE_SUPERADMIN=1` ve `DJANGO_DEBUG=0`

Raw dosya `db`, `redis`, `DATABASE_URL` ve `dokploy-network` dahil tam stack içerir.

---

## Overlay ne işe yarar?

`deploy/dokploy/docker-compose.dokploy.yaml`:

- `app` → `dokploy-network` (Traefik erişimi)
- `traefik.docker.network=dokploy-network` etiketi
- `DATABASE_URL` / `REDIS_URL` yedek tanımı (Dokploy env iletim sorunlarına karşı)

---

## Sorun giderme

| Belirti | Çözüm |
|---------|--------|
| **Restarting (1)** + `DATABASE_URL is missing` | Tam compose deploy; `db`+`redis` konteynerleri var mı? Redeploy |
| **404 page not found** | Domain → servis `app`, port 80; Reload Traefik; sslip → `http://` |
| **DisallowedHost** | Environment'tan `SERVICE_FQDN_APP` / `DJANGO_ALLOWED_HOSTS` sil; Domains kullan |
| **CSRF hatası** | Domains doğru servise bağlı mı? Redeploy |
| **PostgreSQL bağlantı hatası** | `db` healthy mi? 90 sn bekleyin (otomatik retry var) |
| Veri sıfırlandı | `kobiops_gy_data` volume silmeyin |

### Log kontrolü

```bash
docker logs <proje>-app-1 --tail 80
docker ps -a | grep <proje>
```

---

## Kalıcı veri

| Volume | İçerik |
|--------|--------|
| `kobiops_gy_data` | Medya + işaretler |
| `kobiops_gy_postgres` | PostgreSQL |
| `kobiops_gy_redis` | Redis |
| `kobiops_whatsapp_session` | WhatsApp oturumu |

Deploy sırasında volume **silmeyin**.

---

## Ortam şablonları

| Dosya | Açıklama |
|-------|----------|
| [dokploy.env.minimal](dokploy.env.minimal) | Hızlı başlangıç |
| [dokploy.env.example](dokploy.env.example) | Açıklamalı tam şablon |
| [../DOMAIN.md](../DOMAIN.md) | Tüm paneller domain rehberi |
