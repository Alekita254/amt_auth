# The A Million Techies identity server: Keycloak with the `amt` login theme and
# the realm setup scripts. Published as ghcr.io/milliontechies/amt-keycloak.
#
# Production runs it with `start --optimized` (built for PostgreSQL below);
# development can run the same image with `start-dev`.
ARG KEYCLOAK_VERSION=26.8.2

FROM quay.io/keycloak/keycloak:${KEYCLOAK_VERSION} AS builder
ENV KC_DB=postgres \
    KC_HEALTH_ENABLED=true \
    KC_METRICS_ENABLED=true
COPY themes/amt /opt/keycloak/themes/amt
RUN /opt/keycloak/bin/kc.sh build

FROM quay.io/keycloak/keycloak:${KEYCLOAK_VERSION}
COPY --from=builder /opt/keycloak/ /opt/keycloak/
COPY scripts /opt/keycloak/amt-scripts
ENTRYPOINT ["/opt/keycloak/bin/kc.sh"]
CMD ["start", "--optimized"]
