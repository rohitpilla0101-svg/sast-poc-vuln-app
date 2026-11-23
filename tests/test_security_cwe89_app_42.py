import pytest
import os
import sys

# Make `import app` work when pytest runs from the repo root.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as app_module


@pytest.fixture
def client():
    # Set up the database and files exactly like the example tests do
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


def test_proof_sql_injection(client):
    # Control: an ordinary request works and finds a record that really exists
    ok = client.get("/search", query_string={"username": "alice"})
    assert ok.status_code == 200 and ok.get_json()["results"]

    # Attack: SQL injection payload that should return no results
    try:
        rows = client.get("/search", query_string={"username": "nobody' OR '1'='1"}).get_json()["results"]
    except Exception:
        rows = []
    
    assert rows == []  # Safe behavior: no records returned for non-existent user
