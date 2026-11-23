"""Functional tests for tools.py: legitimate use must keep working.

Like tests/test_reports.py, these do NOT assert that the weaknesses are gone: the
autofix pipeline fixes one finding at a time and runs this suite after each fix.
"""
import pytest

import app as app_module
import tools as tools_module


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


def test_ping_reports_reachable_host(client, monkeypatch):
    class Done:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr(tools_module.subprocess, "run", lambda *a, **k: Done())
    resp = client.get("/tools/ping?host=127.0.0.1")
    assert resp.status_code == 200
    assert resp.get_json() == {"host": "127.0.0.1", "reachable": True}


def test_preview_greets_by_name(client):
    resp = client.get("/tools/preview?name=alice")
    assert resp.status_code == 200
    assert b"Hello alice" in resp.data


def test_preview_defaults_to_guest(client):
    assert b"Hello guest" in client.get("/tools/preview").data


def test_token_requires_api_key(client):
    assert client.get("/tools/token?user=alice").status_code == 403
