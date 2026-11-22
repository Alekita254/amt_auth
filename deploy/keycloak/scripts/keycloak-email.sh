#!/usr/bin/env bash
# Connect the realm to a mail server, so "Forgot password?" emails arrive.
# Safe to run again with new values.
#
# Inside the Keycloak container, with your provider's SMTP details:
#   docker compose exec -T \
#     -e SMTP_HOST=smtp.example.com -e SMTP_PORT=587 \
#     -e SMTP_USER=... -e SMTP_PASSWORD=... \
#     -e SMTP_FROM=no-reply@amilliontechies.com \
#     keycloak bash /opt/keycloak/amt-scripts/keycloak-email.sh
#
# Port 587 uses STARTTLS (the default here); for port 465 set SMTP_SSL=true and
# SMTP_STARTTLS=false. Leave SMTP_USER empty for a server without sign-in.
# The password stays in Keycloak's database; nothing is written to the repository.
# Add -e VERIFY_EMAIL=true (or false) to switch email verification for new
# members; without it the current setting is kept.
set -euo pipefail

: "${SMTP_HOST:?Set SMTP_HOST to your mail server, e.g. smtp.gmail.com}"
: "${SMTP_FROM:?Set SMTP_FROM to the address emails come from}"
SMTP_PORT="${SMTP_PORT:-587}"
SMTP_USER="${SMTP_USER:-}"
SMTP_PASSWORD="${SMTP_PASSWORD:-}"
SMTP_STARTTLS="${SMTP_STARTTLS:-true}"
SMTP_SSL="${SMTP_SSL:-false}"
SMTP_FROM_NAME="${SMTP_FROM_NAME:-A Million Techies}"
VERIFY_EMAIL="${VERIFY_EMAIL:-}"

KEYCLOAK_HOME="${KEYCLOAK_HOME:-/opt/keycloak}"
KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
REALM="${REALM:-amilliontechies}"

CONFIG="$(mktemp)"
trap 'rm -f "$CONFIG"' EXIT
kc() { local cmd=$1; shift; "$KEYCLOAK_HOME/bin/kcadm.sh" "$cmd" "$@" --config "$CONFIG"; }

# shellcheck source=kc-login.sh
. "$(dirname "$0")/kc-login.sh"

auth=false
[ -n "$SMTP_USER" ] && auth=true
verify=()
[ -n "$VERIFY_EMAIL" ] && verify=(-s "verifyEmail=$VERIFY_EMAIL")

kc update "realms/$REALM" \
  -s "smtpServer.host=$SMTP_HOST" \
  -s "smtpServer.port=$SMTP_PORT" \
  -s "smtpServer.from=$SMTP_FROM" \
  -s "smtpServer.fromDisplayName=$SMTP_FROM_NAME" \
  -s "smtpServer.starttls=$SMTP_STARTTLS" \
  -s "smtpServer.ssl=$SMTP_SSL" \
  -s "smtpServer.auth=$auth" \
  -s "smtpServer.user=$SMTP_USER" \
  -s "smtpServer.password=$SMTP_PASSWORD" \
  -s resetPasswordAllowed=true \
  "${verify[@]}"

# Saving the settings doesn't contact the server, so check it answers from here:
# a blocked port or a wrong host would otherwise only show when an email goes missing.
# shellcheck disable=SC2016  # $1 and $2 expand in the inner bash
if ! timeout 10 bash -c 'exec 3<>"/dev/tcp/$1/$2"' _ "$SMTP_HOST" "$SMTP_PORT" 2>/dev/null; then
  echo "Can't reach $SMTP_HOST:$SMTP_PORT from the server (blocked port or wrong host)." >&2
  exit 1
fi

echo "Realm '$REALM' sends email through $SMTP_HOST:$SMTP_PORT as $SMTP_FROM."
