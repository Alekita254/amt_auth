#!/usr/bin/env bash
# Sign-up and branding settings for the realm. Safe to run again.
#
# The setup scripts run this at the end. On its own, inside the Keycloak container:
#   docker compose exec -T keycloak bash /opt/keycloak/amt-scripts/keycloak-realm-settings.sh
#
# VERIFY_EMAIL=true makes new members confirm their address (needs a mail server,
# see keycloak-email.sh). CLIENT_ID/FRONTEND_URL point the login pages' "Back to
# Community" link at a frontend; set CLIENT_ID= (empty) to leave clients alone.
set -euo pipefail

KEYCLOAK_HOME="${KEYCLOAK_HOME:-/opt/keycloak}"
KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
REALM="${REALM:-amilliontechies}"
CLIENT_ID="${CLIENT_ID-amt-frontend}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:5173}"
VERIFY_EMAIL="${VERIFY_EMAIL:-false}"

CONFIG="$(mktemp)"
trap 'rm -f "$CONFIG"' EXIT
kc() { local cmd=$1; shift; "$KEYCLOAK_HOME/bin/kcadm.sh" "$cmd" "$@" --config "$CONFIG"; }

# shellcheck source=kc-login.sh
. "$(dirname "$0")/kc-login.sh"

# Branded login pages (themes/amt) and self-service sign-up.
#
# "Forgot password?" emails a reset link, so it only delivers once a mail
# server is configured with keycloak-email.sh. The mail server itself is left
# alone here, so rerunning this keeps it.
kc update "realms/$REALM" \
  -s 'displayName=A Million Techies' \
  -s loginTheme=amt \
  -s registrationAllowed=true \
  -s rememberMe=true \
  -s "verifyEmail=$VERIFY_EMAIL" \
  -s resetPasswordAllowed=true \
  -s loginWithEmailAllowed=true \
  -s duplicateEmailsAllowed=false \
  -s bruteForceProtected=true \
  -s 'passwordPolicy=length(8) and notUsername and notEmail'

# "Back to Community" on the login pages links to the client's base URL.
if [ -n "$CLIENT_ID" ]; then
  frontend="$(kc get clients -r "$REALM" -q clientId="$CLIENT_ID" --fields id --format csv --noquotes)"
  kc update "clients/$frontend" -r "$REALM" -s "rootUrl=$FRONTEND_URL" -s "baseUrl=$FRONTEND_URL/"
fi

echo "Realm '$REALM': sign-up and forgot password on, email verification $VERIFY_EMAIL, login theme 'amt'."
