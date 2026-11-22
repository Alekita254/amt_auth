# Sourced by the setup scripts after they define kc(): signs kcadm in to the
# master realm.
#
# Prefers the amt-deploy service account (KC_ADMIN_CLIENT_SECRET; keycloak-prod-setup.sh
# creates it), which needs no one-time code. Otherwise a user and password:
# KC_ADMIN_USER/KC_ADMIN_PASSWORD, or the bootstrap admin on a fresh server.
if [ -n "${KC_ADMIN_CLIENT_SECRET:-}" ]; then
  kc config credentials --server "$KEYCLOAK_URL" --realm master \
    --client "${KC_ADMIN_CLIENT_ID:-amt-deploy}" --secret "$KC_ADMIN_CLIENT_SECRET"
else
  kc config credentials --server "$KEYCLOAK_URL" --realm master \
    --user "${KC_ADMIN_USER:-${KC_BOOTSTRAP_ADMIN_USERNAME:-admin}}" \
    --password "${KC_ADMIN_PASSWORD:-${KC_BOOTSTRAP_ADMIN_PASSWORD:-admin}}"
fi
