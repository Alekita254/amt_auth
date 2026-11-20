# Identity server: auth.amilliontechies.com

Keycloak and its PostgreSQL database, shared by every A Million Techies product
(Community at `community.amilliontechies.com`, and later Learn, Events…). Products
sign people in here and validate the tokens with [`amt-auth`](https://pypi.org/project/amt-auth/).

| File | What it is |
| --- | --- |
| `Dockerfile` | Keycloak 26.8.2 plus the `amt` login theme (`themes/amt/`) and the setup scripts, published as `ghcr.io/milliontechies/amt-keycloak` |
| `docker-compose.yml` | Production: Keycloak + PostgreSQL 17, Keycloak on `127.0.0.1:8080` only |
| `Caddyfile.snippet` | The site block for the server's Caddy |
| `.env.example` | Settings and secrets; copy to `.env` on the server |
| `backup.sh` | Nightly database dump, copied off the server |
| `scripts/` | Realm setup, run inside the container (they are in the image at `/opt/keycloak/amt-scripts/`) |

## How the sites fit together

```
browser ──► community.amilliontechies.com ──(sign in)──► auth.amilliontechies.com
                     │ backend                                   ▲
                     └── JWKS, service-account token, Admin API ─┘
```

- The browser signs in on `auth.amilliontechies.com` and comes back to the exact URL
  registered for the product's frontend client.
- The product's backend calls `https://auth.amilliontechies.com` for signing keys, its
  service-account token and the realm's Admin REST API.
- The admin console and the `master` realm are **not served publicly**. Caddy answers
  404, and you reach the console through an SSH tunnel.

## First deploy

1. **DNS**: in Cloudflare, add an A record `auth` pointing at the server's IP, set to
   DNS only (grey cloud).
2. **Files**: copy `docker-compose.yml`, `.env.example` and `backup.sh` to the server,
   for example to `/opt/amt-keycloak/`. Then:
   ```bash
   cd /opt/amt-keycloak
   cp .env.example .env && chmod 600 .env
   # fill in DB_PASSWORD and KC_BOOTSTRAP_ADMIN_PASSWORD (openssl rand -base64 32)
   docker compose up -d
   docker compose ps          # keycloak becomes "healthy" after about a minute
   ```
3. **Caddy**: add `Caddyfile.snippet` to the Caddyfile and reload Caddy. If Caddy runs
   in Docker, put it on a network shared with the `keycloak` container and proxy to
   `keycloak:8080`.
4. **Realm and clients**: one pair of clients per product:
   ```bash
   docker compose exec -T -e PRODUCTS="community=https://community.amilliontechies.com" \
     keycloak bash /opt/keycloak/amt-scripts/keycloak-prod-setup.sh
   ```
   It prints `AMT_CLIENT_ID` and `AMT_CLIENT_SECRET` for each new backend. Put them in
   that product's backend env, together with `AMT_KEYCLOAK_URL=https://auth.amilliontechies.com`
   and `AMT_REALM=amilliontechies`. The frontend uses client `<product>-frontend`.
5. **Email**: Keycloak sends verification and password-reset emails. Use the same Zoho
   account Community uses, and check that SPF and DKIM are set up for amilliontechies.com:
   ```bash
   docker compose exec -T -e SMTP_HOST=smtp.zoho.com -e SMTP_PORT=587 \
     -e SMTP_USER=info@amilliontechies.com -e SMTP_PASSWORD='...' \
     -e SMTP_FROM=info@amilliontechies.com \
     keycloak bash /opt/keycloak/amt-scripts/keycloak-email.sh
   ```
6. **Google sign-in**: in the Google OAuth client, add the redirect URI
   `https://auth.amilliontechies.com/realms/amilliontechies/broker/google/endpoint`, then:
   ```bash
   docker compose exec -T -e GOOGLE_CLIENT_ID=... -e GOOGLE_CLIENT_SECRET=... \
     keycloak bash /opt/keycloak/amt-scripts/keycloak-google.sh
   ```
7. **Your admin account**, through the tunnel (see below):
   - In the **master** realm, create your own user, set a password, and give it the
     `admin` role. Sign in as that user, then delete `bootstrap-admin`.
   - In **amilliontechies**, give your member account the realm role `admin` (platform admin).
   - Remove `KC_BOOTSTRAP_ADMIN_USERNAME` and `KC_BOOTSTRAP_ADMIN_PASSWORD` from `.env`,
     then run `docker compose up -d`.
   - The setup scripts now need `-e KC_ADMIN_USER=... -e KC_ADMIN_PASSWORD=...`.
8. **Backups**:
   - Set up an rclone remote for Cloudflare R2 (`rclone config`) and set `BACKUP_REMOTE`
     in `.env`, for example `r2:amt-keycloak-backups`.
   - Add the cron job from the top of `backup.sh`.
   - Do one restore test (below) before going live.

## Checks after deploying

Run these from a machine that isn't the server:

```bash
curl -s https://auth.amilliontechies.com/realms/amilliontechies/.well-known/openid-configuration | grep issuer
# "issuer":"https://auth.amilliontechies.com/realms/amilliontechies"
curl -sI https://auth.amilliontechies.com/admin/ | head -1                 # 404
curl -sI https://auth.amilliontechies.com/realms/master/ | head -1         # 404
curl -sI https://auth.amilliontechies.com/admin/realms/amilliontechies/organizations | head -1  # 401
curl -m 5 http://<server-ip>:8080/  # fails
curl -m 5 http://<server-ip>:9000/  # fails
```

## Admin console (SSH tunnel)

```bash
ssh -L 8080:127.0.0.1:8080 <server>
```

Then open http://localhost:8080/admin. The console's URLs point at
`http://localhost:8080` (`KC_HOSTNAME_ADMIN`), so if port 8080 is already busy on your
machine, stop whatever is using it first.

## Add a product

Run the setup script again with every product listed. Existing clients are updated,
and new ones are created and their secrets printed:

```bash
docker compose exec -T \
  -e PRODUCTS="community=https://community.amilliontechies.com learn=https://learn.amilliontechies.com" \
  keycloak bash /opt/keycloak/amt-scripts/keycloak-prod-setup.sh
```

## Upgrade Keycloak or the theme

1. In this repo, change the theme or bump `ARG KEYCLOAK_VERSION` in the `Dockerfile`
   (read Keycloak's upgrade notes first). Merge, then push a tag
   `keycloak-v<keycloak version>-<n>`, e.g. `keycloak-v26.8.2-2`. CI publishes
   `ghcr.io/milliontechies/amt-keycloak:26.8.2-2`.
2. On the server:
   ```bash
   ./backup.sh                                    # a fresh backup first
   sed -i 's/^KEYCLOAK_IMAGE=.*/KEYCLOAK_IMAGE=ghcr.io\/milliontechies\/amt-keycloak:26.8.2-2/' .env
   docker compose pull keycloak && docker compose up -d
   ```
3. Run the checks above and sign in to a product. To roll back, put the old tag back
   in `.env`. After a Keycloak *version* change, also restore the backup taken in step 2,
   because Keycloak migrates the database on start.

## Restore a backup

```bash
docker compose stop keycloak
docker compose exec -T db pg_restore -U keycloak -d keycloak --clean --if-exists --no-owner \
  < backups/keycloak-<timestamp>.dump      # or fetch one first: rclone copy $BACKUP_REMOTE/<file> backups/
docker compose start keycloak
```

To test a backup without touching production, run the same steps in a scratch copy:
use a different project name (`docker compose -p amt-keycloak-restore ...`) with a
compose override that publishes another port, then sign in against it.
