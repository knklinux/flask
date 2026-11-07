"""Tests for the session cookie name prefix and attribute requirements."""

from __future__ import annotations

import pytest

import flask


def _app(name: str, **config: object) -> flask.Flask:
    app = flask.Flask(__name__)
    app.testing = True
    app.secret_key = "test"
    app.config["SESSION_COOKIE_NAME"] = name
    app.config.update(config)

    @app.route("/")
    def index() -> str:
        flask.session["x"] = 1
        return "ok"

    @app.route("/read")
    def read() -> str:
        return str(flask.session.get("x"))

    return app


@pytest.mark.parametrize(
    ("name", "config"),
    [
        ("__Host-session", {"SESSION_COOKIE_SECURE": True}),
        ("__Secure-session", {"SESSION_COOKIE_SECURE": True}),
        ("session", {}),
        ("__host-session", {}),
    ],
)
def test_accepted_configuration(name, config):
    """Configurations browsers accept still set a cookie that round-trips."""
    app = _app(name, **config)
    client = app.test_client()
    assert client.get("/").status_code == 200
    assert client.get("/read").get_data(as_text=True) == "1"


@pytest.mark.parametrize(
    ("name", "config", "match"),
    [
        (
            "__Host-session",
            {"SESSION_COOKIE_SECURE": True, "SESSION_COOKIE_DOMAIN": ".example.com"},
            "SESSION_COOKIE_DOMAIN",
        ),
        (
            "__Host-session",
            {"SESSION_COOKIE_SECURE": True, "SESSION_COOKIE_PATH": "/app"},
            "SESSION_COOKIE_PATH",
        ),
        ("__Host-session", {}, "SESSION_COOKIE_SECURE"),
        ("__Secure-session", {}, "SESSION_COOKIE_SECURE"),
    ],
)
def test_rejected_configuration(name, config, match):
    """A prefix whose requirements are not met is reported, not silently sent."""
    app = _app(name, **config)

    with pytest.raises(RuntimeError, match=match):
        app.test_client().get("/")


def test_partitioned_requires_secure():
    app = _app("session", SESSION_COOKIE_PARTITIONED=True)

    with pytest.raises(RuntimeError, match="PARTITIONED"):
        app.test_client().get("/")


def test_partitioned_with_secure_is_accepted():
    app = _app("session", SESSION_COOKIE_PARTITIONED=True, SESSION_COOKIE_SECURE=True)
    response = app.test_client().get("/")
    header = response.headers["Set-Cookie"]

    assert "Partitioned" in header
    assert "Secure" in header
