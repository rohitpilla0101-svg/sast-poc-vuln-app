# sample-vuln-app

Deliberately vulnerable Flask app used as a demo target for the
sast-autofix-poc pipeline. Do not deploy this anywhere reachable.

> **Client demo (Semgrep scan + manual approval, no LLM):** see
> [DEMO-APPROVAL-GATE.md](DEMO-APPROVAL-GATE.md). The original LLM autofix PoC
> is preserved at tag `poc-llm-autofix-v1` and in `poc-archive/llm-autofix/`.

## Bugs (for demo narration)

1. `GET /search?username=...` — SQL injection (CWE-89), string-interpolated
   query.
2. `GET /files/<path:filename>` — path traversal (CWE-22), no containment
   check before `send_file`.
3. `GET /admin/data?username=...` — role cached per-client-address instead
   of per-username, so a shared NAT/proxy client can read back another
   user's cached admin role (race/logic bug, not a canned CWE snippet).

## Run

    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt
    python app.py
