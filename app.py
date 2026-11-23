import hashlib
import hmac
import os
import sqlite3
import threading
from urllib.parse import urlparse

from flask import Flask, request, send_from_directory, abort, redirect, render_template

from reports import reports

app = Flask(__name__)
app.register_blueprint(reports)

DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "uploads")

# per-process cache of the last-checked role, keyed by a value that is NOT
# unique per request under concurrency (see /admin/data below).
_role_cache = {}
_role_cache_lock = threading.Lock()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute(
        "CREATE TABLE IF NOT EXISTS users ("
        "id INTEGER PRIMARY KEY, username TEXT, role TEXT)"
    )
    conn.execute("DELETE FROM users")
    conn.executemany(
        "INSERT INTO users (username, role) VALUES (?, ?)",
        [("alice", "admin"), ("bob", "user"), ("carol", "user")],
    )
    conn.commit()
    conn.close()


@app.route("/search")
def search_users():
    """SQL injection: username is string-interpolated directly into the query."""
    username = request.args.get("username", "")
    conn = get_db()
    rows = conn.execute(
        "SELECT id, username, role FROM users WHERE username = ?", (username,)
    ).fetchall()
    conn.close()
    return {"results": [dict(r) for r in rows]}


@app.route("/files/<path:filename>")
def get_file(filename):
    """Serve file securely from uploads directory."""
    return send_from_directory(UPLOADS_DIR, filename)


@app.route("/admin/data")
def admin_data():
    """Custom logic bug: role is resolved by a background thread and cached
    per-process keyed by request.remote_addr, not per-request. Under
    concurrent requests from behind the same proxy/NAT, one caller's
    elevated role can be read back by a different, less-privileged caller
    before the cache entry is refreshed for their own username."""
    username = request.args.get("username", "")
    client_key = request.remote_addr  # not unique per user behind shared NAT/proxy

    with _role_cache_lock:
        cached = _role_cache.get(client_key)

    if cached is None:
        conn = get_db()
        row = conn.execute(
            "SELECT role FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()
        role = row["role"] if row else "user"
        with _role_cache_lock:
            _role_cache[client_key] = role
    else:
        role = cached  # stale/foreign role served from cache, not re-checked

    if role != "admin":
        abort(403)

    return {"secret": "admin-only payload", "served_role": role}


# --- user accounts feature -------------------------------------------------

_passwords = {}


def _hash_password_internal(password: str, salt: bytes) -> tuple[bytes, bytes]:
    """Hash password using scrypt. Returns (salt, digest)."""
    digest = hashlib.scrypt(
        password.encode(),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
        dklen=32
    )
    return salt, digest


def hash_password(password: str) -> str:
    """Hash a password and store the result in format 'scrypt${salt_hex}${digest_hex}'."""
    salt = os.urandom(16)
    _, digest = _hash_password_internal(password, salt)
    return f"scrypt${salt.hex()}${digest.hex()}"


def check_password(password: str, hashed: str) -> bool:
    """Verify a password against a stored hash."""
    try:
        parts = hashed.split("$")
        if len(parts) != 3 or parts[0] != "scrypt":
            return False
        salt_hex, digest_hex = parts[1], parts[2]
        salt = bytes.fromhex(salt_hex)
        stored_digest = bytes.fromhex(digest_hex)

        _, computed_digest = _hash_password_internal(password, salt)
        
        # Use constant-time comparison to prevent timing attacks
        return hmac.compare_digest(computed_digest, stored_digest)
    except (ValueError, IndexError):
        return False


@app.route("/register", methods=["POST"])
def register():
    username = request.form["username"]
    _passwords[username] = hash_password(request.form["password"])
    return {"registered": username}


@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    if not check_password(request.form["password"], _passwords.get(username, "")):
        abort(401)
    next_url = request.args.get("next", "/")
    parsed = urlparse(next_url)
    if not parsed.netloc or parsed.netloc == request.host:
        return redirect(parsed.path + ("?" + parsed.query if parsed.query else ""))
    abort(403)


@app.route("/welcome")
def welcome():
    name = request.args.get("name", "guest")
    return render_template("welcome.html", name=name)


if __name__ == "__main__":
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=False)
