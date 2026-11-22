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
| `deploy.sh` | Pull from GitHub, back up, rebuild, restart, rerun the realm setup, check |
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
- The admin console and the `master` realm are served only on
  `auth-admin.amilliontechies.com` (`KC_HOSTNAME_ADMIN`). On `auth.amilliontechies.com`
  Caddy answers 404 for them. Every admin signs in with a password and a code from an
  authenticator app.

## First deploy

1. **DNS**: in Cloudflare, add A records `auth` and `auth-admin` pointing at the
   server's IP, set to DNS only (grey cloud).
2. **Files**: copy `docker-compose.yml`, `.env.example` and `backup.sh` to the server,
   for example to `/opt/amt-keycloak/`. Then:
   ```bash
   cd /opt/amt-keycloak
   cp .env.example .env && chmod 600 .env
   # fill in DB_PASSWORD and KC_BOOTSTRAP_ADMIN_PASSWORD (openssl rand -base64 32),
   # and PROXY_NETWORK: the Docker network the Caddy container is on
   docker compose up -d
   docker compose ps          # amt-keycloak becomes "healthy" after about a minute
   ```
3. **Caddy**: add `Caddyfile.snippet` to the Caddyfile, then reload Caddy. Caddy runs in
   Docker and reaches Keycloak as `amt-keycloak:8080` over `PROXY_NETWORK`. The services
   are prefixed `amt-` because that network is shared: a bare `keycloak` would clash
   with another project's Keycloak in Docker's DNS.
4. **Realm and clients**: one pair of clients per product:
   ```bash
   docker compose exec -T -e PRODUCTS="community=https://community.amilliontechies.com" \
     amt-keycloak bash /opt/keycloak/amt-scripts/keycloak-prod-setup.sh
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
     amt-keycloak bash /opt/keycloak/amt-scripts/keycloak-email.sh
   ```
6. **Google sign-in**: in the Google OAuth client, add the redirect URI
   `https://auth.amilliontechies.com/realms/amilliontechies/broker/google/endpoint`, then:
   ```bash
   docker compose exec -T -e GOOGLE_CLIENT_ID=... -e GOOGLE_CLIENT_SECRET=... \
     amt-keycloak bash /opt/keycloak/amt-scripts/keycloak-google.sh
   ```
7. **Your admin account**, at https://auth-admin.amilliontechies.com:
   - Step 4 printed `KC_ADMIN_CLIENT_SECRET` for the `amt-deploy` service account. Put it
     in `.env`; `deploy.sh` and the setup scripts sign in with it from now on.
   - In the **master** realm, create your own user, set a password, and give it the
     `admin` role. Sign in as that user (you'll set up an authenticator app), then
     delete `bootstrap-admin`.
   - In **amilliontechies**, give your member account the realm role `admin` (platform admin).
   - Remove `KC_BOOTSTRAP_ADMIN_USERNAME` and `KC_BOOTSTRAP_ADMIN_PASSWORD` from `.env`,
     then run `docker compose up -d`.
   - Running a script by hand now needs `-e KC_ADMIN_CLIENT_SECRET=...`.
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
curl -sI https://auth-admin.amilliontechies.com/ | head -1                 # 302 to the console
curl -sI https://auth-admin.amilliontechies.com/realms/amilliontechies/account/ | head -1  # 404
curl -sI https://auth.amilliontechies.com/admin/realms/amilliontechies/organizations | head -1  # 401
curl -m 5 http://<server-ip>:8080/  # fails
curl -m 5 http://<server-ip>:9000/  # fails
```

## Admin console

Open https://auth-admin.amilliontechies.com. There are two realms:

- **master**: admins only, for the admin console. No sign-up, and only on the admin
  hostname. Admins need a password and an authenticator-app code; the setup script
  asks every admin without an app to set one up on their next sign-in, and locks an
  account for a while after 5 wrong passwords.
- **amilliontechies**: every member, shared by all products. `https://auth.amilliontechies.com`
  opens its account page (profile, password, passkeys). Products send people to it
  through their own client (`community-frontend`, ...).

The setup script points the master realm's Frontend URL at `KC_HOSTNAME_ADMIN`.
Without it the console's sign-in check goes to the public host, where
`/realms/master` is blocked, and stops with "Timeout when waiting for 3rd party check
iframe message".

To keep the console off the internet instead, set `KC_HOSTNAME_ADMIN=http://localhost:8080`,
drop the `auth-admin` site from Caddy, rerun the setup, and use an SSH tunnel:
`ssh -L 8080:127.0.0.1:8080 <server>`, then http://localhost:8080/admin.

## Deploy updates

After merging to the branch the server tracks, on the server:

```bash
/var/www/projects/amt-auth/deploy/keycloak/deploy.sh
```

It pulls (fast-forward only), backs up the database, builds the image from the
checkout under the `KEYCLOAK_IMAGE` tag, runs `docker compose up -d`, waits until
Keycloak is healthy, reruns `keycloak-prod-setup.sh` for `PRODUCTS`, and checks the
public URL. The realm setup needs `PRODUCTS` and `KC_ADMIN_CLIENT_SECRET` (the
`amt-deploy` service account) in `.env`; without them that step is skipped. Skip steps
with `--no-pull`, `--no-backup` or `--no-setup`.

## Add a product

Run the setup script again with every product listed. Existing clients are updated,
and new ones are created and their secrets printed:

```bash
docker compose exec -T \
  -e PRODUCTS="community=https://community.amilliontechies.com learn=https://learn.amilliontechies.com" \
  amt-keycloak bash /opt/keycloak/amt-scripts/keycloak-prod-setup.sh
```

A product's web app signs in only from the URLs listed for it. To let it sign in from
somewhere else too, such as a staging site or developers' machines, add those URLs after
its own, separated by commas:

```bash
PRODUCTS="community=https://community.amilliontechies.com,http://localhost:5173"
```

Put the same list in `.env` so `deploy.sh` keeps it. Listing a product again without a
URL removes that URL from its client.

## Upgrade Keycloak or the theme

1. In this repo, change the theme or bump `ARG KEYCLOAK_VERSION` in the `Dockerfile`
   (read Keycloak's upgrade notes first). Merge, then push a tag
   `keycloak-v<keycloak version>-<n>`, e.g. `keycloak-v26.8.2-2`. CI publishes
   `ghcr.io/milliontechies/amt-keycloak:26.8.2-2`.
2. On the server:
   ```bash
   ./backup.sh                                    # a fresh backup first
   sed -i 's/^KEYCLOAK_IMAGE=.*/KEYCLOAK_IMAGE=ghcr.io\/milliontechies\/amt-keycloak:26.8.2-2/' .env
   docker compose pull amt-keycloak && docker compose up -d
   ```
3. Run the checks above and sign in to a product. To roll back, put the old tag back
   in `.env`. After a Keycloak *version* change, also restore the backup taken in step 2,
   because Keycloak migrates the database on start.

## Restore a backup

```bash
docker compose stop amt-keycloak
docker compose exec -T amt-keycloak-db pg_restore -U keycloak -d keycloak --clean --if-exists --no-owner \
  < backups/keycloak-<timestamp>.dump      # or fetch one first: rclone copy $BACKUP_REMOTE/<file> backups/
docker compose start amt-keycloak
```

To test a backup without touching production, run the same steps in a scratch copy:
use a different project name (`docker compose -p amt-keycloak-restore ...`) with a
compose override that publishes another port, then sign in against it.
