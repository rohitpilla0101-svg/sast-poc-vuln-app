#!/usr/bin/env python3
"""Turn a Semgrep JSON report into PR feedback for the approval-gate demo.

No LLM and no auto-fix: this only reports. Subcommand:

  report   read semgrep.json, write the job summary, emit file annotations,
           upsert one sticky PR comment, and set the step output `findings`.

Dry run (no GitHub calls): python semgrep_gate.py report semgrep.json --dry-run
"""
import argparse
import json
import os
import subprocess
import sys

MARKER = "<!-- semgrep-gate -->"
SEVERITY_RANK = {"INFO": 0, "WARNING": 1, "ERROR": 2}
SEVERITY_ICON = {"ERROR": "🔴", "WARNING": "🟠", "INFO": "🔵"}
MAX_LISTED = 40  # keep the comment far below GitHub's 65,536 char limit


def sh(args, check=True):
    return subprocess.run(args, capture_output=True, text=True, check=check)


def gh_api(*args, check=True):
    return sh(["gh", "api", *args], check=check)


def load_findings(path, min_severity):
    with open(path, encoding="utf-8", errors="replace") as f:
        data = json.load(f)
    floor = SEVERITY_RANK[min_severity]
    findings = []
    for r in data.get("results", []):
        extra = r.get("extra", {})
        sev = extra.get("severity", "INFO").upper()
        if SEVERITY_RANK.get(sev, 0) < floor:
            continue
        meta = extra.get("metadata", {}) or {}
        cwe = meta.get("cwe") or []
        if isinstance(cwe, str):
            cwe = [cwe]
        findings.append(
            {
                "severity": sev,
                "rule": r.get("check_id", "unknown"),
                "path": r.get("path", "").replace("\\", "/"),
                "line": r.get("start", {}).get("line", 1),
                "end_line": r.get("end", {}).get("line", 1),
                "message": " ".join(extra.get("message", "").split()),
                "cwe": cwe[0].split(":")[0] if cwe else "",
                "refs": (meta.get("references") or [])[:2],
            }
        )
    findings.sort(key=lambda f: (-SEVERITY_RANK.get(f["severity"], 0), f["path"], f["line"]))
    return findings


def source_snippet(path, start, end):
    # Semgrep hides `extra.lines` ("requires login") for registry rules when
    # not logged in, so read the code from the checkout instead.
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
        return "\n".join(lines[start - 1 : min(end, start + 6)])
    except OSError:
        return ""


def build_comment(findings, ctx):
    n = len(findings)
    sev_counts = {}
    for f in findings:
        sev_counts[f["severity"]] = sev_counts.get(f["severity"], 0) + 1
    breakdown = ", ".join(
        f"{SEVERITY_ICON[s]} {c} {s.lower()}"
        for s, c in sorted(sev_counts.items(), key=lambda kv: -SEVERITY_RANK[kv[0]])
    )
    out = [
        MARKER,
        f"## 🛡️ Semgrep found {n} security issue{'s' if n != 1 else ''} in this PR",
        "",
        f"{breakdown} · scanned `{ctx['sha'][:7]}` · [workflow run]({ctx['run_url']})",
        "",
        "| Severity | Rule | Location | CWE |",
        "|---|---|---|---|",
    ]
    for f in findings[:MAX_LISTED]:
        loc = f"[`{f['path']}:{f['line']}`]({ctx['blob']}/{f['path']}#L{f['line']})"
        rule = f["rule"].split(".")[-1]
        out.append(f"| {SEVERITY_ICON[f['severity']]} {f['severity']} | `{rule}` | {loc} | {f['cwe'] or '–'} |")
    if n > MAX_LISTED:
        out.append(f"\n_…and {n - MAX_LISTED} more — see the workflow run summary._")
    out += ["", "<details><summary>Details and flagged code</summary>", ""]
    for f in findings[:MAX_LISTED]:
        out.append(f"**{f['path']}:{f['line']}** — {f['message']}")
        snippet = source_snippet(f["path"], f["line"], f["end_line"])
        if snippet:
            out += ["```", snippet, "```"]
        out.append("")
    out += ["</details>", ""]
    out += [
        "### Next step",
        "",
        "Review the findings above and fix them, or have a maintainer review and accept the risk, before merging.",
        "",
        "_Report only: nothing is auto-fixed and no new branch is created._",
    ]
    return "\n".join(out)


def upsert_comment(repo, pr, body):
    r = gh_api(f"repos/{repo}/issues/{pr}/comments", "--paginate", "--jq",
               f'.[] | select(.body | startswith("{MARKER}")) | .id')
    ids = r.stdout.split()
    if ids:
        gh_api("--method", "PATCH", f"repos/{repo}/issues/comments/{ids[0]}", "-f", f"body={body}")
    else:
        gh_api("--method", "POST", f"repos/{repo}/issues/{pr}/comments", "-f", f"body={body}")


def write_output(name, value):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{name}={value}\n")


def cmd_report(args):
    repo = os.environ.get("GITHUB_REPOSITORY", "owner/repo")
    sha = os.environ.get("PR_HEAD_SHA", "0000000")
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    ctx = {
        "sha": sha,
        "run_url": f"{server}/{repo}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '0')}",
        "blob": f"{server}/{repo}/blob/{sha}",
    }
    findings = load_findings(args.input, args.min_severity)
    write_output("findings", len(findings))
    pr = os.environ.get("PR_NUMBER")
    post = not args.dry_run and pr and args.comment
    if not findings:
        print("No Semgrep findings at or above", args.min_severity)
        if post:
            upsert_comment(
                repo, pr,
                f"{MARKER}\n## ✅ Semgrep: no security issues found\n\nScanned `{sha[:7]}` · "
                f"[workflow run]({ctx['run_url']})",
            )
        return 0

    body = build_comment(findings, ctx)
    for f in findings:  # inline annotations on the PR's Files tab
        title = f"Semgrep {f['severity']}: {f['rule'].split('.')[-1]}"
        level = "error" if f["severity"] == "ERROR" else "warning"
        print(f"::{level} file={f['path']},line={f['line']},title={title}::{f['message']}")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(body.replace(MARKER, "") + "\n")
    if args.dry_run:
        print(body)
    elif post:
        upsert_comment(repo, pr, body)
    return 0


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # emoji in output; Windows consoles default to cp1252
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("report")
    r.add_argument("input")
    r.add_argument("--min-severity", default=os.environ.get("MIN_SEVERITY", "WARNING"),
                   choices=list(SEVERITY_RANK))
    r.add_argument("--no-comment", dest="comment", action="store_false")
    r.add_argument("--dry-run", action="store_true")
    r.set_defaults(func=cmd_report)
    args = p.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
