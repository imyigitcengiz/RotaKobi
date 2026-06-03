# CoolOPS — Plesk dağıtımı

Domain otomatik: `deploy.sh` vhost yolundan veya `KOBIOPS_DOMAIN` → [DOMAIN.md](../DOMAIN.md)  
Env: [plesk.env.example](plesk.env.example) · Stacks: [plesk-stack.env.example](plesk-stack.env.example)

Plesk’te iki yol desteklenir. **Önerilen:** Git + otomatik deploy script (güncelleme kolay). **Alternatif:** Plesk **Docker** eklentisi → **Stacks** (tamamen panelden).

| | Git + `deploy.sh` | Docker Stacks |
|--|-------------------|-----------------|
| Güncelleme | Push / Pull now | Stack → Up / Git pull + Up |
| Compose | `docker-compose.yaml` + overlay | `docker-compose.plesk-stack.yaml` |
| Nginx | Ek directives (proxy) | Aynı |
| Deneyim | Coolify benzeri otomasyon | Panel UI |

## Gereksinimler

- Plesk Obsidian 18.0.53+
- **Docker** eklentisi (Extensions → Docker → Install)
- **Git** eklentisi (Yöntem A için)
- RAM ≥ 2 GB (WhatsApp köprüsü + Chromium)
- SSH (ilk kurulum, Docker kurulumu)

Docker yoksa (SSH, bir kez):

```bash
sudo bash deploy/plesk/install-docker.sh
```

---

## Ortak: domain ve reverse proxy

1. **Websites & Domains** → subdomain ekleyin: `ops.ornek.com`
2. **SSL/TLS** → Let’s Encrypt
3. **Apache & nginx Settings** → **Proxy mode** açık
4. **Additional nginx directives** → `deploy/plesk/nginx-proxy.conf` içeriğini yapıştırın  
   (hedef port varsayılan **8000** — `plesk.env` içinde `KOBIOPS_HTTP_PORT` değiştirdiyseniz proxy’de de güncelleyin)

### Neden kök `docker-compose.yaml`'da `ports` yok?

Ana dosya Coolify/Dokploy için tasarlandı (`expose` only). Plesk’te host portu **overlay** ile açılır:

```yaml
# deploy/plesk/docker-compose.plesk.yaml
ports:
  - "127.0.0.1:8000:80"   # dışarıdan değil — Plesk nginx buraya proxy yapar
```

Sadece `docker compose up` (overlay olmadan) çalıştırırsanız dış port **kapalı** kalır → 502 / Passenger hatası.

**Doğru komut:** `./deploy/plesk/deploy.sh` veya  
`COMPOSE_FILE=docker-compose.yaml:deploy/plesk/docker-compose.plesk.yaml docker compose up -d --build`

Sunucuda test: `curl http://127.0.0.1:8000/healthz/`

Uygulama konteyner içinde **80** dinler; Plesk nginx → `127.0.0.1:8000`.

---

## Yöntem A — Git otomatik deploy (önerilen)

### 1) Git deposu

**Domains → ops.ornek.com → Git**

| Alan | Değer |
|------|--------|
| URL | `https://github.com/imyigitcengiz/cool-ops.git` |
| Branch | `main` |
| Deployment mode | **Automatic** |
| Deploy to | Subdomain document root |

**Additional deployment actions** (her pull/deploy sonrası):

```bash
/bin/bash deploy/plesk/deploy.sh
```

Tam yol gerekirse:

```bash
/bin/bash /var/www/vhosts/ANA_DOMAIN/ops.ornek.com/deploy/plesk/deploy.sh
```

### 2) İlk kurulum (SSH — bir kez)

```bash
cd /var/www/vhosts/ANA_DOMAIN/ops.ornek.com   # Plesk’teki gerçek yol

cp deploy/plesk/plesk.env.example deploy/plesk/plesk.env
nano deploy/plesk/plesk.env   # KOBIOPS_DOMAIN=ops.ornek.com

chmod +x deploy/plesk/deploy.sh
./deploy/plesk/deploy.sh
```

### 3) Giriş

`https://ops.ornek.com/giris/` — ilk kurulum: **admin** / **admin** (hemen değiştirin).

`plesk.env` içinde sonra: `DJANGO_ENSURE_SUPERADMIN=0` ve yeniden deploy.

### 4) Güncelleme

- GitHub push → Plesk webhook veya **Pull now**
- Script otomatik `docker compose up -d --build` çalıştırır

---

## Yöntem B — Plesk Docker Stacks (konteyner paneli)

Repo’yu domain köküne alın (Git veya SFTP):

```bash
cd /var/www/vhosts/ANA_DOMAIN/ops.ornek.com
git clone https://github.com/imyigitcengiz/cool-ops.git .
```

**Extensions → Docker → Stacks → Add Stack**

| Alan | Değer |
|------|--------|
| Project name | `cool-ops` |
| Kaynak | **Webspace** |
| Domain | `ops.ornek.com` |
| Compose file | `deploy/plesk/docker-compose.plesk-stack.yaml` |

**Stack ortam değişkenleri** (Editor veya env dosyası):

```env
KOBIOPS_DOMAIN=ops.ornek.com
KOBIOPS_HTTP_PORT=8000
KOBIOPS_PUBLIC_URL=https://ops.ornek.com
DJANGO_ENSURE_SUPERADMIN=1
```

Şablon: `deploy/plesk/plesk-stack.env.example`

**Up** (pull + build) — ilk sefer 5–15 dk. Sonra nginx proxy (yukarıdaki gibi) ve `https://ops.ornek.com/giris/`.

> Stacks, repodaki `Dockerfile` ile imajı domain home içinde derler. Compose dosyası yalnızca YAML değil; tüm repo webspace’te olmalı.

### COMPOSE_FILE ile (gelişmiş)

Stack env:

```env
COMPOSE_FILE=docker-compose.yaml:deploy/plesk/docker-compose.plesk.yaml
KOBIOPS_DOMAIN=ops.ornek.com
```

Compose path: `docker-compose.yaml`

---

## Kalıcı veri

| Volume | İçerik |
|--------|--------|
| `kobiops_gy_data` | SQLite, medya, yedekler |
| `kobiops_whatsapp_session` | WhatsApp oturumu |

Stack veya `docker compose down` sırasında **volume silmeyin**.

---

## Log ve kontrol

```bash
tail -f deploy/plesk/logs/deploy.log
docker compose -f docker-compose.yaml -f deploy/plesk/docker-compose.plesk.yaml ps
docker compose logs app --tail 80
docker compose logs whatsapp_bridge --tail 50
```

---

## Sorun giderme

| Belirti | Çözüm |
|---------|--------|
| 502 Bad Gateway | `docker compose ps` — `app` healthy mi? nginx `proxy_pass` portu **8000** mi? `curl http://127.0.0.1:8000/healthz/` |
| DisallowedHost | `KOBIOPS_DOMAIN` doğru; redeploy |
| CSRF | SSL açık; `KOBIOPS_PUBLIC_URL=https://...` |
| `/data kalıcı volume` | Volume silinmiş; `kobiops_gy_data` yeniden oluşsun, veri yedekten |
| Docker permission denied | `usermod -aG docker <user>` veya deploy root ile |
| Stack build hatası | RAM ≥ 2 GB; `docker compose logs` |
| Deploy script çalışmıyor | `/bin/bash` + tam path; `chmod +x deploy/plesk/deploy.sh` |

---

## Dosyalar

| Dosya | Açıklama |
|-------|----------|
| `deploy/plesk/deploy.sh` | Git post-deploy hook |
| `deploy/plesk/docker-compose.plesk.yaml` | Git/CLI overlay (localhost:8000→80) |
| `deploy/plesk/docker-compose.plesk-stack.yaml` | Plesk Stacks (include + port) |
| `deploy/plesk/plesk.env` | Sunucu domain ayarı (gitignore) |
| `deploy/plesk/plesk-stack.env` | Stacks UI env (gitignore) |
| `deploy/plesk/nginx-proxy.conf` | Plesk nginx snippet |
| `deploy/plesk/install-docker.sh` | Docker kurulum yardımcısı |

Genel: [deploy/README.md](../README.md) · [DEPLOY.md](../../DEPLOY.md)
