import pytest
from amt_auth.core.config import load_config
from amt_auth.exceptions import ConfigError

BASE = {
    "AMT_KEYCLOAK_URL": "http://localhost:8080",
    "AMT_REALM": "amilliontechies",
    "AMT_CLIENT_ID": "amilliontechies-web",
    "AMT_CLIENT_SECRET": "secret",
}


def test_all_vars_present():
    cfg = load_config(BASE)
    assert cfg.keycloak_url == "http://localhost:8080"
    assert cfg.realm == "amilliontechies"
    assert cfg.client_id == "amilliontechies-web"
    assert cfg.client_secret == "secret"


@pytest.mark.parametrize(
    "missing",
    ["AMT_KEYCLOAK_URL", "AMT_REALM", "AMT_CLIENT_ID", "AMT_CLIENT_SECRET"],
)
def test_missing_var_raises(missing):
    env = {k: v for k, v in BASE.items() if k != missing}
    with pytest.raises(ConfigError):
        load_config(env)


def test_malformed_url_raises():
    env = {**BASE, "AMT_KEYCLOAK_URL": "localhost:8080"}  # no scheme
    with pytest.raises(ConfigError):
        load_config(env)


def test_trailing_slash_stripped():
    env = {**BASE, "AMT_KEYCLOAK_URL": "http://localhost:8080/"}
    cfg = load_config(env)
    assert not cfg.keycloak_url.endswith("/")


def test_load_config_idempotent():
    cfg1 = load_config(BASE)
    cfg2 = load_config(BASE)
    assert cfg1 == cfg2
