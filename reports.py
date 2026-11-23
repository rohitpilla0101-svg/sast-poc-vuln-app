"""Report downloads and webhook sync: a small feature module for the gate demo.

Deliberately imperfect (Medium and Low findings only, see the commit message).
"""

import hashlib
import os
import sqlite3

import requests
from flask import Blueprint, Response, jsonify, request

reports = Blueprint("reports", __name__, url_prefix="/reports")

SYNC_URL = os.environ.get("REPORTS_SYNC_URL", "https://sync.internal.example/reports")

_REPORTS = {
    "weekly": "Weekly summary: 12 tickets opened, 9 closed",
    "monthly": "Monthly summary: 51 tickets opened, 47 closed",
}


def etag(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


@reports.route("/<name>")
def download(name):
    content = _REPORTS.get(name)
    if content is None:
        return jsonify({"error": "no such report"}), 404
    resp = Response(content, mimetype="text/plain")
    resp.headers["ETag"] = etag(content)
    return resp


@reports.route("/sync", methods=["POST"])
def sync():
    payload = {"reports": sorted(_REPORTS), "requested_by": request.headers.get("X-Requested-By", "")}
    resp = requests.post(SYNC_URL, json=payload, timeout=5)
    return jsonify({"status": resp.status_code})


@reports.route("/search")
def search():
    term = request.args.get("q", "")
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE names (name TEXT)")
    conn.executemany("INSERT INTO names VALUES (?)", [(n,) for n in sorted(_REPORTS)])
    rows = conn.execute("SELECT name FROM names WHERE name LIKE ?", (f"%{term}%",)).fetchall()
    return jsonify({"results": [r[0] for r in rows]})


def cache_key(name: str) -> str:
    return hashlib.sha256(name.encode()).hexdigest()


@reports.route("/<name>/cache-key")
def cache_key_for(name):
    if name not in _REPORTS:
        return jsonify({"error": "no such report"}), 404
    return jsonify({"report": name, "cache_key": cache_key(name)})
