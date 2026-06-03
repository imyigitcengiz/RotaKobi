# CoolOPS — 1Panel kurulumu (tak-çalıştır)

1Panel **Docker Compose Stack** ile panel + WhatsApp köprüsü birlikte çalışır.

Domain otomatik: stack env **`KOBIOPS_DOMAIN`** → `SERVICE_FQDN_APP` (bootstrap).  
Detay: [DOMAIN.md](../DOMAIN.md) · Env: [1panel.env.example](1panel.env.example)

## Hızlı kurulum (SSH)

```bash
cd /opt
git clone https://github.com/imyigitcengiz/cool-ops.git
cd cool-ops
chmod +x deploy/install.sh
./deploy/install.sh panel.sizin-domain.com
```

`install.sh` `.env` üretir (`KOBIOPS_DOMAIN` dahil), `docker compose up -d --build` çalıştırır.

Domain yoksa: `./deploy/install.sh` → `http://SUNUCU_IP:8000/giris/`

## 1Panel arayüzü ile

1. **Konteyner** → **Compose** → **Oluştur**
2. **Kaynak:** `/opt/cool-ops` (mutlak yol)
3. **Compose dosyası:** `docker-compose.yaml`
4. **Ortam değişkenleri:** [1panel.env.example](1panel.env.example) içeriğini yapıştırın  
   (`COMPOSE_FILE=...1panel.yaml` zorunlu — port 80 çakışmasını önler)
5. **Web sitesi** → reverse proxy → `http://127.0.0.1:8080`
6. Stack env'de `KOBIOPS_DOMAIN=panel.sizin-domain.com` → **Deploy**

## Kalıcı veri

| Volume | Mount |
|--------|--------|
| `kobiops_gy_data` | `/data` |
| `kobiops_whatsapp_session` | WhatsApp oturumu |

## İlk giriş

- `https://panel.sizin-domain.com/giris/`
- **admin** / **admin** → sonra `DJANGO_ENSURE_SUPERADMIN=0`

## Sorun giderme

| Belirti | Çözüm |
|---------|--------|
| Container yok | **Compose** sekmesi; `COMPOSE_FILE=...1panel.yaml` |
| 502 | Proxy `127.0.0.1:8080`; `docker compose ps` |
| CSRF / DisallowedHost | `KOBIOPS_DOMAIN` doğru; redeploy |
| Elle APP_URL yazmayın | [DOMAIN.md](../DOMAIN.md) |

Detay: [DEPLOY.md](../../DEPLOY.md)
