# GY Panel — üretim kurulumu

Bu ürün **müşteri başına ayrı kurulum** içindir (her müşteri kendi VPS / panelinde). Tek kod tabanı; Coolify, 1Panel, Portainer, Railway veya `docker compose` ile dağıtılabilir.

## Bileşenler

| Bileşen | Açıklama |
|--------|----------|
| **app** | Django + Daphne (port 8000), SQLite + medya `/data` altında |
| **whatsapp-bridge** | Node + Chromium, WhatsApp Web QR (port 3939, iç ağ) |

Panel konteynerinde Node/Puppeteer **yoktur**. Köprü ayrı servistir.

## Hızlı başlangıç (önerilen)

```bash
git clone https://github.com/imyigitcengiz/gy-dashboard-py.git
cd gy-dashboard-py
cp deploy/coolify/.env.example .env
# .env içinde DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS, DJANGO_CSRF_TRUSTED_ORIGINS doldurun

docker compose up -d --build
```

- Panel: `http://sunucu:8000/giris/`
- İlk giriş: `DJANGO_ENSURE_SUPERADMIN=1` ise `admin` / `admin` (sonra kapatın)

## Ortam değişkenleri (app)

| Değişken | Zorunlu | Açıklama |
|----------|---------|----------|
| `DJANGO_SECRET_KEY` | Evet | Uzun rastgele anahtar |
| `DJANGO_ALLOWED_HOSTS` | Evet | `panel.ornek.com` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | HTTPS ise | `https://panel.ornek.com` |
| `DATA_DIR` | Docker’da otomatik | `/data` — kalıcı volume bağlayın |
| `WHATSAPP_BRIDGE_URL` | WhatsApp için | Compose’ta: `http://whatsapp-bridge:3939` |
| `DJANGO_WHATSAPP_BRIDGE_CAN_SPAWN` | Docker’da `0` | Panel içinden Node başlatmayı kapatır |

## Kalıcı veri

Volume **`/data`**:

- `/data/db.sqlite3` — veritabanı
- `/data/media/` — yüklenen dosyalar

Yedek: Araçlar → Sistem yedeği (SQLite indir) + `media/` klasörünü kopyalayın.

## Coolify

1. **Docker Compose** veya iki uygulama:
   - Uygulama 1: repo kökü, `Dockerfile`, port **8000**, volume `/data`
   - Uygulama 2 (isteğe bağlı ayrı): `deploy/whatsapp-bridge/Dockerfile`, port 3939 (dışarı açmayın)
2. Aynı Docker ağında: `WHATSAPP_BRIDGE_URL=http://<köprü-servis-adı>:3939`
3. `DJANGO_WHATSAPP_BRIDGE_CAN_SPAWN=0`
4. Tek Dockerfile ile sadece panel kurulursa WhatsApp **çalışmaz** — köprü servisi şart.

Detay: [deploy/coolify/README.md](deploy/coolify/README.md)

## 1Panel / Portainer

`compose.yaml` dosyasını “Stack” olarak içe aktarın; `.env` ve reverse proxy (443 → 8000) ayarlayın.

## Yerel geliştirme (Windows)

```bash
pip install -r requirements.txt
python manage.py migrate
# İsteğe bağlı otomatik köprü:
set DJANGO_WHATSAPP_BRIDGE_AUTO_START=1
python manage.py runserver
```

Köprüyü elle: `cd tools/whatsapp_bridge && npm install && npm start`

`WHATSAPP_BRIDGE_URL=http://127.0.0.1:3939` ve `DJANGO_WHATSAPP_BRIDGE_CAN_SPAWN=1` (varsayılan, `DATA_DIR` yokken).

## Sorun giderme — “Köprü çalışmıyor”

1. `docker compose ps` — `whatsapp-bridge` **healthy** mi?
2. App loglarında `WHATSAPP_BRIDGE_URL` doğru mu? (`http://whatsapp-bridge:3939` compose içinde)
3. Köprü logları: `docker compose logs whatsapp-bridge`
4. Sadece panel konteyneri varsa: ikinci servisi ekleyin veya harici köprü URL’si verin.

“Başlatılıyor…” sonsuz döngüsü eski sürümde yerel port kontrolünden kaynaklanıyordu; güncel kod uzak URL’ye HTTP ile bakar.

## Ekip sohbeti

Deploy sonrası otomatik: `migrate` + `ensure_chat` (entrypoint).

Reverse proxy (Coolify / Traefik / Nginx) WebSocket için:

```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

WebSocket kapalı olsa bile sohbet **HTTP ile** çalışır (4 sn polling). Sohbet açılmıyorsa panelde kırmızı hata metni görünür; çoğunlukla `python manage.py migrate chat` eksiktir.
