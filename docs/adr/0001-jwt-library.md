# ADR-0001: Use PyJWT as the JWT validation library

**Status**: Accepted  
**Date**: 2026-11-14  
**Phase**: A

## Context

`amt-auth` must verify RS256-signed JWTs issued by Keycloak. Three libraries were considered:

| Library | Status | Notes |
|---|---|---|
| `python-jose` | Effectively unmaintained (last release 2022, open CVEs) | Ruled out |
| `authlib` | Actively maintained, broad protocol support | Too heavy for a focused library dep |
| `PyJWT` | Actively maintained, narrow scope, RSA support via `cryptography` extra | Chosen |

## Decision

Use `PyJWT[crypto]` (pins `cryptography` as a transitive dep).

## Consequences

- `get_unverified_header` lets us extract `kid` and reject non-RS256 algorithms before fetching JWKS.
- `jwt.decode` with `algorithms=["RS256"]` and explicit `issuer`/`audience` checks satisfies Keycloak's token format.
- Algorithm-confusion attacks (`alg: none`, HS256) are blocked at the header-inspection step before any key material is involved.
- If Keycloak ever needs ES256 tokens, we add `"ES256"` to `_ALLOWED_ALGORITHMS` and confirm `cryptography` already supports ECDSA keys.
