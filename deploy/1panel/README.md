# CoolOPS — 1Panel kurulumu (tak-çalıştır)

1Panel **Docker Compose Stack** ile panel + WhatsApp köprüsü birlikte çalışır.

## Hızlı kurulum (SSH)

```bash
cd /opt
git clone https://github.com/imyigitcengiz/cool-ops.git
cd cool-ops
chmod +x deploy/install.sh
./deploy/install.sh panel.sizin-domain.com
```

`install.sh` `.env` üretir, secret/host/CSRF ayarlar, `docker compose up -d --build` çalıştırır.

Domain yoksa: `./deploy/install.sh` → `http://SUNUCU_IP:8000/giris/`

## 1Panel arayüzü ile

1. **Konteyner** → **Compose** → **Oluştur**
2. **Kaynak:** `/opt/cool-ops` (klonladığınız dizin — mutlak yol)
3. **Compose dosyası:** `docker-compose.yaml`
4. **Ortam değişkeni** (1Panel stack ayarlarında):
   ```
   COMPOSE_FILE=docker-compose.yaml:deploy/1panel/docker-compose.1panel.yaml
   ```
   > 1Panel zaten **80** portunu kullanır. Varsayılan compose host'ta `80:80` açmaya çalışır ve **başarısız olur** — container listesi boş kalır.
5. **Başlat / Deploy** — ilk build 5–15 dk sürebilir

Container'lar **Konteyner → Compose** altında stack adı `cool-ops` ile görünür; tek tek **Konteyner** listesinde hemen çıkmayabilir.

İsteğe bağlı `.env`: `cp .env.example .env`

## Reverse proxy (HTTPS)

1Panel **Web sitesi** / OpenResty:

- Domain → proxy `http://127.0.0.1:8080` (yukarıdaki 1Panel overlay ile)
- WebSocket açık (ekip sohbeti)

Domain ekledikten sonra redeploy veya `./deploy/install.sh panel.sizin-domain.com --force`

## Kalıcı veri

| Volume | Mount | İçerik |
|--------|--------|--------|
| `kobiops_gy_data` | `/data` | SQLite, medya, yedekler |
| `coolops_whatsapp_session` | köprü oturumu | WhatsApp QR |

Stack silinirken **volume silmeyin**.

## İlk giriş

- `https://panel.sizin-domain.com/giris/`
- **admin** / **admin** → sonra `DJANGO_ENSURE_SUPERADMIN=0`

## Güncelleme

```bash
cd /opt/cool-ops
git pull
docker compose up -d --build
```

## Sorun giderme

| Belirti | Çözüm |
|---------|--------|
| Container görünmüyor | **Compose** sekmesine bakın (stack `cool-ops`). SSH: `cd /opt/cool-ops && docker compose ps -a` |
| Compose hemen düşüyor | Muhtemelen **port 80 çakışması** — `COMPOSE_FILE=...1panel.yaml` kullanın veya `docker compose logs` |
| Build hatası | `docker compose logs app --tail 100` — RAM ≥ 2 GB |
| 502 | Reverse proxy hedefi `127.0.0.1:8080` mi? `docker compose ps` |
| CSRF | `./deploy/install.sh domain --force` |
| WhatsApp | `docker compose logs whatsapp_bridge` |
| Veri kaybı | Volume korundu mu? |

Detay: [DEPLOY.md](../../DEPLOY.md)
