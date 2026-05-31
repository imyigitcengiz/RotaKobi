# Easypanel kurulumu

[Easypanel](https://easypanel.io/) → **Create** → **Docker Compose** → GitHub repo.

| Ayar | Değer |
|------|--------|
| Repo | `imyigitcengiz/kobi-ops` |
| Compose file | `docker-compose.yaml` |
| Service domain | **`app`** servisi, container port **80** |

Easypanel Traefik kullanır; ana `docker-compose.yaml` yeterlidir (host `ports` yok).

İsteğe bağlı ortam: `DJANGO_ENSURE_SUPERADMIN=1` (ilk giriş), sonra `0`.

Genel: [deploy/README.md](../README.md)
