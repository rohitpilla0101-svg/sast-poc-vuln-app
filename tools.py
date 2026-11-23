"""Admin tools: host diagnostics, greeting preview, session import and API tokens.

Deliberately vulnerable (Critical and High findings) so the feature gate blocks
the push and sast-autofix opens a fix PR. Do not deploy.
"""

import base64
import hashlib
import pickle
import subprocess

from flask import Blueprint, jsonify, render_template_string, request

tools = Blueprint("tools", __name__, url_prefix="/tools")

ADMIN_API_KEY = "demo-admin-key-7f3c9a1e5b2d"  # CWE-798: hardcoded credential


@tools.route("/ping")
def ping():
    host = request.args.get("host", "127.0.0.1")
    # CWE-78: user input reaches a shell
    result = subprocess.run(f"ping -c 1 {host}", shell=True, capture_output=True, text=True)
    return jsonify({"host": host, "reachable": result.returncode == 0})


@tools.route("/preview")
def preview():
    name = request.args.get("name", "guest")
    # CWE-1336: user input becomes part of the Jinja template (SSTI)
    return render_template_string("<p>Hello " + name + "</p>")


@tools.route("/session/import", methods=["POST"])
def import_session():
    # CWE-502: untrusted bytes are unpickled
    session = pickle.loads(base64.b64decode(request.get_data()))
    return jsonify({"keys": sorted(session)})


@tools.route("/token")
def token():
    if request.headers.get("X-Api-Key") != ADMIN_API_KEY:
        return jsonify({"error": "forbidden"}), 403
    user = request.args.get("user", "")
    # CWE-327: MD5 used to derive a security token
    return jsonify({"user": user, "token": hashlib.md5(user.encode()).hexdigest()})
