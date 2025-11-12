# Production Deployment (gps.it-uae.com)

This guide explains how to deploy the tracker stack (Postgres + FastAPI backend + React frontend + Caddy reverse proxy) on a production server `gps.it-uae.com`.

## 1. Prerequisites

- Ubuntu/Debian server with SSH access: `ssh root@gps.it-uae.com`
- DNS A record for `gps.it-uae.com` pointing to the server's IP.
- Docker and Docker Compose plugin installed.

Install Docker (if not present):

```bash
curl -fsSL https://get.docker.com | sh
systemctl enable docker --now
```

Verify:
```bash
docker version
docker compose version
```

## 2. Clone Repository

```bash
ssh root@gps.it-uae.com
git clone https://github.com/your-org/your-repo.git tracker
cd tracker/deploy
```

> Adjust repo URL to your private/public repository.

## 3. Environment Configuration

Backend settings are controlled by environment variables. In production compose file we set:

- `DATABASE_URL`: points to Postgres service.
- `CORS_ORIGINS`: includes `https://gps.it-uae.com`.
- Frontend build arg `VITE_API_BASE` set to `https://gps.it-uae.com/api` and `VITE_WS_BASE` to `wss://gps.it-uae.com`.

If you need secrets (e.g., 2GIS key), edit `docker-compose.prod.yml` build args or use a `.env` file.

## 4. TLS & Reverse Proxy (Caddy)

`deploy/caddy/Caddyfile` configures automatic HTTPS via Let's Encrypt:

- Proxies `/api` and `/ws` paths to backend.
- All other paths go to the frontend container.
- WebSockets are supported automatically by Caddy.

## 5. Build & Start

From `deploy/` directory:

```bash
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

Check containers:
```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f backend
```

Initial migrations/DB init run automatically via backend startup command (if coded). If needed, you can execute seed scripts:
```bash
docker compose -f docker-compose.prod.yml exec backend python seed_hd35_week.py
```

## 6. Health Verification

Browser: open `https://gps.it-uae.com`.

API check:
```bash
curl -s https://gps.it-uae.com/api/health | jq
curl -s "https://gps.it-uae.com/api/devices" | jq
```

WebSocket test (optional):
Use `wscat` locally:
```bash
npm i -g wscat
wscat -c "wss://gps.it-uae.com/ws/tracker?devices=13"
```

## 7. Updating

Pull new code & rebuild:
```bash
cd /root/tracker
git pull
docker compose -f deploy/docker-compose.prod.yml build
docker compose -f deploy/docker-compose.prod.yml up -d
```

## 8. Logs & Maintenance

Tail logs:
```bash
docker compose -f deploy/docker-compose.prod.yml logs -f backend frontend caddy
```

Backup Postgres (basic dump):
```bash
docker compose -f deploy/docker-compose.prod.yml exec postgres pg_dump -U traccar traccar > backup.sql
```

## 9. Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| 404 on /api | Proxy misroute | Check Caddyfile path prefixes |
| Mixed Content | Using http front | Ensure HTTPS DNS & Caddy running |
| CORS errors | Missing origin | Add domain to `CORS_ORIGINS` |
| WebSocket close immediately | Wrong query param | Pass `?devices=ID1,ID2` |

## 10. Scaling Notes

- Move Postgres to managed service or attach persistent volume snapshots.
- Add monitoring (Prometheus + caddy metrics, etc.).
- Horizontal scaling: run multiple backend replicas behind Caddy (add upstreams in Caddyfile).

## 11. Security Hardening

- Create non-root deploy user.
- Restrict SSH with key auth only.
- Rotate TLS via Caddy (automatic). Disable unused ports in firewall (allow 80/443 only). Use UFW:
```bash
ufw allow OpenSSH
ufw allow 80
ufw allow 443
ufw enable
```

## 12. Optional: Enable 2GIS Tiles

Edit `docker-compose.prod.yml` frontend build args:
```yaml
      args:
        VITE_API_BASE: https://gps.it-uae.com/api
        VITE_WS_BASE: wss://gps.it-uae.com
        VITE_MAP_PROVIDER: 2gis
        VITE_2GIS_KEY: YOUR_KEY
```
Rebuild frontend:
```bash
docker compose -f deploy/docker-compose.prod.yml build frontend
docker compose -f deploy/docker-compose.prod.yml up -d frontend
```

---
Deployment complete. Open `https://gps.it-uae.com` to use the tracker.
