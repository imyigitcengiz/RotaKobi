# Portainer Stack kurulumu

[Portainer](https://www.portainer.io/) → **Stacks** → **Add stack** → Git repository.

## Ayarlar

| Alan | Değer |
|------|--------|
| Repository | `https://github.com/imyigitcengiz/kobi-ops` |
| Compose path | `docker-compose.yaml` |
| Environment | `COMPOSE_FILE=docker-compose.yaml:deploy/portainer/docker-compose.portainer.yaml` |

## Reverse proxy

Uygulama `127.0.0.1:8080` dinler. Nginx Proxy Manager veya sunucu nginx:

```nginx
proxy_pass http://127.0.0.1:8080;
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

## Kalıcı veri

Volume **`kobiops_gy_data`** silinmeden kalmalı.

Genel: [deploy/README.md](../README.md) · [DEPLOY.md](../../DEPLOY.md)
