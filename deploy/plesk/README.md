# KobiOps — Plesk Git otomatik deploy

Plesk **Git** ile `pull` + `deploy` sonrası Docker stack otomatik güncellenir.

## Gereksinimler

- Plesk Obsidian (Git eklentisi)
- SSH erişimi (ilk kurulum için)
- Docker + Docker Compose v2 (`docker compose`)
- RAM ≥ 2 GB (WhatsApp köprüsü için)

## 1) Subdomain

1. **Websites & Domains** → subdomain ekle: `ops.yigitcengiz.co`
2. **SSL/TLS** → Let's Encrypt ile sertifika al
3. **Apache & nginx Settings** → **Proxy mode** açık
4. **Additional nginx directives** → `deploy/plesk/nginx-proxy.conf` içeriğini yapıştır  
   (port `8080` — `plesk.env` ile değiştirdiyseniz proxy'de de güncelleyin)

## 2) Git deposu (Plesk panel)

**Domains → ops.yigitcengiz.co → Git**

| Alan | Değer |
|------|--------|
| URL | `https://github.com/imyigitcengiz/kobi-ops.git` |
| Branch | `main` |
| Deployment mode | **Automatic** (veya Manual + Deploy now) |
| Deploy to | Subdomain document root (ör. `/ops.yigitcengiz.co`) |

**Additional deployment actions** (kritik — her pull/deploy sonrası çalışır):

```bash
/bin/bash deploy/plesk/deploy.sh
```

Tam yol gerekirse (Plesk sürümüne göre):

```bash
/bin/bash /var/www/vhosts/YOUR_DOMAIN/ops.yigitcengiz.co/deploy/plesk/deploy.sh
```

## 3) İlk kurulum (SSH — bir kez)

```bash
cd /var/www/vhosts/yigitcengiz.co/ops.yigitcengiz.co   # Plesk'teki gerçek yol

# Domain ayarı (sunucuya özel — git'e gitmez)
cp deploy/plesk/plesk.env.example deploy/plesk/plesk.env
nano deploy/plesk/plesk.env   # KOBIOPS_DOMAIN=ops.yigitcengiz.co

chmod +x deploy/plesk/deploy.sh

# Docker yoksa
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker

# İlk deploy
./deploy/plesk/deploy.sh
```

Panel: `https://ops.yigitcengiz.co/giris/` — ilk giriş `admin` / `admin` (hemen değiştirin).

`plesk.env` içinde sonra: `DJANGO_ENSURE_SUPERADMIN=0`

## 4) Günlük kullanım

- Plesk Git → **Pull now** veya **Deploy now** → script otomatik `docker compose up -d --build` çalıştırır
- GitHub push ile otomatik: Plesk Git sayfasındaki **Webhook URL**'yi GitHub repo → Settings → Webhooks'a ekleyin

## 5) Log

```bash
tail -f deploy/plesk/logs/deploy.log
docker compose -f docker-compose.yaml -f deploy/plesk/docker-compose.plesk.yaml logs -f app
```

## Sorun giderme

| Belirti | Çözüm |
|---------|--------|
| 502 Bad Gateway | `docker compose ps` — app ayakta mı? nginx proxy port 8080 mi? |
| DisallowedHost | `plesk.env` → doğru `KOBIOPS_DOMAIN`, redeploy |
| CSRF hatası | SSL açık + domain doğru; redeploy |
| Docker permission denied | `usermod -aG docker PLESK_USER` veya script root ile |
| Deploy script çalışmıyor | Additional actions'ta `/bin/bash` ile tam path; `chmod +x deploy/plesk/deploy.sh` |

## Dosyalar

| Dosya | Açıklama |
|-------|----------|
| `deploy/plesk/deploy.sh` | Plesk post-deploy hook |
| `deploy/plesk/docker-compose.plesk.yaml` | localhost:8080 bind |
| `deploy/plesk/plesk.env` | Sunucuya özel domain (gitignore) |
| `deploy/plesk/nginx-proxy.conf` | Plesk nginx snippet |
