# ADR-0002: In-memory JWKS cache with kid-based re-fetch on miss

**Status**: Accepted  
**Date**: 2026-11-14  
**Phase**: A

## Context

Keycloak signs tokens with RSA keys identified by a `kid` header. Keys are exposed at the
public JWKS endpoint. The library must fetch these keys without adding an external cache
dependency and must handle Keycloak key-rotation gracefully.

## Options considered

| Option | Trade-off |
|---|---|
| TTL-only (re-fetch every N minutes) | Re-fetches even when nothing changed; stale cache window between rotation and TTL expiry |
| External cache (Redis) | Adds an infrastructure dependency inappropriate for a library |
| In-memory dict, re-fetch on unknown kid | Zero extra deps; handles rotation by re-fetching when an unknown kid arrives |

## Decision

Use an in-memory `dict[kid → RSAPublicKey]`. On a cache miss, fetch the JWKS endpoint
once; if the kid is still absent (key rotation may have *just* happened), fetch once more.
If still absent, raise `InvalidTokenError`.

Two fetches maximum per unknown kid keeps latency bounded. After a successful fetch, all
returned keys are cached, so subsequent valid tokens have zero network overhead.

## Consequences

- No external dependency; safe to use inside any Django process.
- Two network round-trips in the worst case (key rotation race). Acceptable for the
  frequency at which Keycloak rotates signing keys (months, not seconds).
- Cache is per-process, per-`JWKSClient` instance. Under Django, `AuthService` should
  be instantiated at module level (not per-request) so the cache is shared across
  requests within a worker process.
- Thread safety: in CPython, dict reads/writes under the GIL are safe enough for this
  use case. If this library is used with an async server in future phases, revisit.
