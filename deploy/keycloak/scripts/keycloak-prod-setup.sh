#!/usr/bin/env bash
# Set up (or bring up to date) the production realm and one pair of clients per
# product. Safe to run again: everything is created if missing, updated if not.
#
# Inside the Keycloak container:
#   docker compose exec -T \
#     -e PRODUCTS="community=https://community.amilliontechies.com" \
#     amt-keycloak bash /opt/keycloak/amt-scripts/keycloak-prod-setup.sh
#
# PRODUCTS is a space-separated list of name=URL. Each product gets:
#   <name>-frontend  public client (PKCE), sign-in only from URL
#   <name>-backend   confidential client whose service account calls the Admin API
# A backend's secret is printed once, when the client is created. To read it
# again: Clients > <name>-backend > Credentials in the admin console.
#
# No users are created. Configure email with keycloak-email.sh and Google with
# keycloak-google.sh afterwards.
set -euo pipefail

: "${PRODUCTS:?Set PRODUCTS, e.g. PRODUCTS=\"community=https://community.amilliontechies.com\"}"
KEYCLOAK_HOME="${KEYCLOAK_HOME:-/opt/keycloak}"
KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
REALM="${REALM:-amilliontechies}"
SCRIPTS="$(dirname "$0")"

CONFIG="$(mktemp)"
trap 'rm -f "$CONFIG"' EXIT
kc() { local cmd=$1; shift; "$KEYCLOAK_HOME/bin/kcadm.sh" "$cmd" "$@" --config "$CONFIG"; }
csv() { kc get "$@" --format csv --noquotes; }
client_id_of() { csv clients -r "$REALM" -q clientId="$1" --fields id,clientId | grep ",$1\$" | cut -d, -f1 || true; }
has_mapper() { csv "$1/protocol-mappers/models" -r "$REALM" --fields name | grep -qx "$2"; }

kc config credentials --server "$KEYCLOAK_URL" --realm master \
  --user "${KC_ADMIN_USER:-${KC_BOOTSTRAP_ADMIN_USERNAME:-admin}}" \
  --password "${KC_ADMIN_PASSWORD:-${KC_BOOTSTRAP_ADMIN_PASSWORD:-admin}}"

# --- Realm -----------------------------------------------------------------------

if ! kc get "realms/$REALM" --fields realm >/dev/null 2>&1; then
  kc create realms -s realm="$REALM" -s enabled=true
  echo "Created realm '$REALM'."
fi

# Organizations; admin events (what changed in organizations); the login event
# log (who signed up and signed in), kept for 30 days; passkeys.
kc update "realms/$REALM" \
  -s organizationsEnabled=true \
  -s adminEventsEnabled=true -s adminEventsDetailsEnabled=true \
  -s eventsEnabled=true -s eventsExpiration=2592000 \
  -s 'enabledEventTypes=["REGISTER","LOGIN","LOGIN_ERROR","VERIFY_EMAIL","UPDATE_PASSWORD"]' \
  -s webAuthnPolicyPasswordlessPasskeysEnabled=true

csv roles -r "$REALM" --fields name | grep -qx admin \
  || kc create roles -r "$REALM" -s name=admin  # platform admins

# The organization scope puts memberships in the token. By default it is a bare
# list of aliases; amt-auth needs the organization IDs and the user's groups.
org_scope="$(csv client-scopes -r "$REALM" --fields id,name | grep ',organization$' | cut -d, -f1)"
org_scope_path="client-scopes/$org_scope"
org_mapper="$(csv "$org_scope_path/protocol-mappers/models" -r "$REALM" --fields id,protocolMapper \
  | grep ',oidc-organization-membership-mapper$' | cut -d, -f1)"
kc update "$org_scope_path/protocol-mappers/models/$org_mapper" -r "$REALM" \
  -s 'config.addOrganizationId=true' -s 'config."jsonType.label"=JSON'
has_mapper "$org_scope_path" organization-groups \
  || kc create "$org_scope_path/protocol-mappers/models" -r "$REALM" \
    -s name=organization-groups -s protocol=openid-connect \
    -s protocolMapper=oidc-organization-group-membership-mapper \
    -s 'config."access.token.claim"=true' -s 'config."id.token.claim"=true'

admin_api_scope="$(csv client-scopes -r "$REALM" --fields id,name | grep ',kc-admin-api$' | cut -d, -f1)"

# --- Clients, one pair per product -----------------------------------------------

# upsert_client <clientId> <kcadm -s settings...>: prints the client's internal id.
upsert_client() {
  local client=$1; shift
  local id
  id="$(client_id_of "$client")"
  if [ -n "$id" ]; then
    kc update "clients/$id" -r "$REALM" "$@"
  else
    kc create clients -r "$REALM" -s clientId="$client" "$@" >/dev/null 2>&1
    id="$(client_id_of "$client")"
    echo "Created client '$client'." >&2
  fi
  echo "$id"
}

for product in $PRODUCTS; do
  name="${product%%=*}"
  url="${product#*=}"
  url="${url%/}"
  if [ "$name" = "$product" ] || [[ ! "$url" =~ ^https?://[^/*]+$ ]]; then
    echo "Skipping '$product': expected name=https://host (no path, no wildcard)." >&2
    continue
  fi

  # Backend: no browser sign-in, only its own service account.
  backend_created=0
  [ -n "$(client_id_of "$name-backend")" ] || backend_created=1
  backend="$(upsert_client "$name-backend" \
    -s publicClient=false -s serviceAccountsEnabled=true \
    -s standardFlowEnabled=false -s directAccessGrantsEnabled=false \
    -s implicitFlowEnabled=false)"
  # Without the kc-admin-api scope the Admin API answers 401.
  kc update "clients/$backend/default-client-scopes/$admin_api_scope" -r "$REALM"
  kc add-roles -r "$REALM" --uusername "service-account-$name-backend" --cclientid realm-management \
    --rolename manage-organizations --rolename view-organizations \
    --rolename manage-users --rolename view-users --rolename query-users --rolename query-groups

  # Frontend: public client with PKCE, allowed to redirect back to its own site only.
  frontend="$(upsert_client "$name-frontend" \
    -s publicClient=true -s standardFlowEnabled=true \
    -s directAccessGrantsEnabled=false -s implicitFlowEnabled=false \
    -s "rootUrl=$url" -s "baseUrl=$url/" \
    -s "redirectUris=[\"$url/*\"]" -s "webOrigins=[\"$url\"]" \
    -s 'attributes."pkce.code.challenge.method"=S256' \
    -s "attributes.\"post.logout.redirect.uris\"=$url/*")"
  # Its tokens must be valid for its backend, which checks `aud` against AMT_CLIENT_ID.
  has_mapper "clients/$frontend" "$name-backend-audience" \
    || kc create "clients/$frontend/protocol-mappers/models" -r "$REALM" \
      -s name="$name-backend-audience" -s protocol=openid-connect -s protocolMapper=oidc-audience-mapper \
      -s "config.\"included.client.audience\"=$name-backend" -s 'config."access.token.claim"=true'

  echo "Product '$name': $name-frontend signs in from $url, $name-backend calls the Admin API."
  if [ "$backend_created" = 1 ]; then
    secret="$(kc get "clients/$backend/client-secret" -r "$REALM" --fields value --format csv --noquotes)"
    echo "  AMT_CLIENT_ID=$name-backend"
    echo "  AMT_CLIENT_SECRET=$secret   (shown once; store it in $name's backend env)"
  fi
done

# --- Sign-up, theme, brute-force protection, password policy ----------------------

CLIENT_ID='' VERIFY_EMAIL=true bash "$SCRIPTS/keycloak-realm-settings.sh"

echo
echo "Realm '$REALM' is ready at its issuer: \$KC_HOSTNAME/realms/$REALM"
