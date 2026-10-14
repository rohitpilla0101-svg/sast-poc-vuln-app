# Demo: Semgrep scan reported on the pull request

Client-facing demo. Scans every pull request with Semgrep and reports the
findings on the PR. Report only.

**No LLM, no auto-fix, no fix branch, no approval step.** The earlier LLM
autofix PoC is kept untouched: git tag `poc-llm-autofix-v1`, branch
`backup/llm-autofix-poc`, and the archived workflow in
`poc-archive/llm-autofix/`. An approve/reject variant (environment required
reviewers, which needs a paid plan on private repos) is archived in
`poc-archive/environment-approval/`.

## Flow

```
PR opened / updated
        |
  [Semgrep scan]  -- clean --> check green, comment "no issues"
        |
     findings
        |
  PR comment with findings table + flagged code,
  annotations on the changed lines, scan check fails
```

Files:

- `.github/workflows/semgrep-approval-gate.yml` - the workflow (name: Semgrep Approval Gate).
- `.github/scripts/semgrep_gate.py` - builds the PR comment, annotations and summary.

Only findings **new in the PR** are reported (`--baseline-commit` against the
PR base), at severity `WARNING` or higher (`MIN_SEVERITY` in the workflow).
Ruleset: `p/python`, `p/flask`, `p/security-audit` (no Semgrep login needed);
edit the `semgrep scan --config` flags to change it.

## Setup

1. A self-hosted runner with the label `sast-gate` must be online (python,
   git and gh on PATH). Locally: `cd C:\actions-runner; .\run.cmd`.
2. GitHub Actions must be able to start jobs for the account (a billing lock
   stops every job, including self-hosted ones).
3. The workflow must exist on the branch your PRs target (this demo lives on
   `client-demo`; merge it into `main` when ready).

## Run the demo

```
gh pr create --base client-demo --head demo/vulnerable-change \
  --title "Add user search" --body "Demo PR with a SQL injection"
```

`demo/vulnerable-change` reintroduces the original SQL injection (and the
`0.0.0.0` bind) in `app.py`. The **Semgrep scan** check fails and the PR gets
the findings comment. Open a PR without security issues to show the clean path.
