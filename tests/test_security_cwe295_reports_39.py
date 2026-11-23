import pytest
import requests

import app as app_module


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


def test_proof_tls_verification_is_not_disabled(client, monkeypatch):
    # Control: ensure the endpoint works normally
    resp = client.get("/reports/weekly")
    assert resp.status_code == 200

    calls = []

    class Reply:
        status_code = 200

    def fake_post(*args, **kwargs):
        calls.append(kwargs)
        return Reply()

    monkeypatch.setattr(requests, "post", fake_post)
    
    # Trigger the sync endpoint which makes the vulnerable request
    resp = client.post("/reports/sync", headers={"X-Requested-By": "test"})
    
    assert resp.status_code == 200
    
    # Verify that verify=False was not passed in any call
    assert calls, "No outgoing HTTP call was made"
    assert all(kw.get("verify", True) is not False for kw in calls)
