import pytest

import app as app_module


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


def test_proof_command_injection(client, tmp_path):
    canary = tmp_path / "pwned"
    # control: an ordinary value works
    assert client.get("/tools/ping", query_string={"host": "127.0.0.1"}).status_code == 200
    try:
        # the trailing " #" makes the shell ignore anything the application appends after the value
        client.get("/tools/ping", query_string={"host": f"x; touch {canary} #"})
    except Exception:
        pass
    assert not canary.exists()
