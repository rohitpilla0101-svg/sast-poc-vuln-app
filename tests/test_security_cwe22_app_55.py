import os
import pytest

import app as app_module


@pytest.fixture
def client():
    os.makedirs(app_module.UPLOADS_DIR, exist_ok=True)
    sample = os.path.join(app_module.UPLOADS_DIR, "hello.txt")
    with open(sample, "w") as f:
        f.write("hello from uploads")
    app_module.init_db()
    app_module._role_cache.clear()
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c
    os.remove(sample)


def test_proof_path_traversal(client):
    served = app_module.UPLOADS_DIR
    assert client.get("/files/hello.txt").status_code == 200
    canary = os.path.join(os.path.dirname(served), "canary_secret.txt")
    with open(canary, "w") as f:
        f.write("TOP-SECRET-CANARY")
    try:
        try:
            resp = client.get("/files/..%2Fcanary_secret.txt")
            leaked = resp.status_code == 200 and b"TOP-SECRET-CANARY" in resp.data
        except Exception:
            leaked = False
    finally:
        os.remove(canary)
    assert not leaked
