import pytest

import app as app_module


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


def test_proof_script_is_not_reflected(client):
    # Control: normal request should work
    assert client.get("/tools/preview", query_string={"name": "alice"}).status_code == 200

    # Test XSS payload
    try:
        body = client.get("/tools/preview", query_string={"name": "<script>alert(1)</script>"}).get_data(as_text=True)
    except Exception:
        body = ""
    
    # Test SSTI payload
    try:
        math = client.get("/tools/preview", query_string={"name": "{{1337*3}}"}).get_data(as_text=True)
    except Exception:
        math = ""

    # Assert that the malicious payloads are not reflected in the output
    assert "<script>alert(1)</script>" not in body
    assert "4011" not in math
