# JWKS key fetching and caching is handled by jwt.PyJWKClient (PyJWT ≥ 2.4).
# TokenValidator constructs a PyJWKClient from the realm JWKS URI automatically.
# There is no custom caching or rotation logic here — PyJWT owns that.
#
# If you need to inject a custom client in tests, pass jwks_client= to TokenValidator.
