# Demo: Semgrep scan + manual approval gate

Client-facing demo. Scans every pull request with Semgrep, reports the findings
on the PR, then waits for a human to approve (merge) or reject (close).

**No LLM, no auto-fix, no fix branch.** The earlier LLM autofix PoC is kept
untouched in the original repo: git tag `poc-llm-autofix-v1`, branch
`backup/llm-autofix-poc`, and the archived workflow in
`poc-archive/llm-autofix/`.

## Flow

```
PR opened / updated
        |
  [Semgrep scan]  -- clean --> check green, PR mergeable as usual
        |
     findings
        |
  PR comment with findings table + file annotations; scan check fails
        |
  [Security approval]  <-- pauses: reviewer opens the run -> "Review deployments"
      /          \
 Approve        Reject
    |              |
 [Merge PR]   [Close PR]    (comment names the reviewer)
```

`Security gate` is the aggregate check and the one required by branch
protection: green when the scan is clean or a reviewer approved, red while
pending or rejected. The GitHub merge button stays blocked until a decision.

Only findings **new in the PR** are reported (`--baseline-commit` against the
PR base), at severity `WARNING` or higher (`MIN_SEVERITY` in the workflow).
Ruleset: `p/python`, `p/flask`, `p/security-audit` (no Semgrep login needed).

## Setup (already done on this repo)

1. Repo is **public** - environment required reviewers and branch protection
   are free there (private repos need a paid plan).
2. Self-hosted runner with label `sast-gate` online:
   `cd C:\actions-runner-demo; .\run.cmd` (python, git and gh on PATH).
3. Approval environment: `scripts/setup-approval-environment.sh owner/repo reviewer-login`
   (creates `security-approval` with required reviewers).
4. Branch protection on `main`: required status check **Security gate**,
   admins included. Fork-PR policy: approval required for all outside
   contributors (the runner executes PR code - never approve unknown PRs).

If the environment has no reviewers the workflow fails closed: the gate stays
red and the PR comment says the environment is not configured.

## Run the demo

```
gh pr create --base main --head demo/vulnerable-change \
  --title "Add user search" --body "Demo PR with a SQL injection"
```

`demo/vulnerable-change` reintroduces the original SQL injection (and the
`0.0.0.0` bind) in `app.py`. Then:

1. **Semgrep scan** fails; the PR gets a findings comment; merge is blocked.
2. Open the workflow run -> **Review deployments** -> Approve or Reject.
3. Approve: gate turns green and the PR is merged. Reject: the PR is closed.
   Either way a comment records who decided.

Clean path: a PR with no security issues passes the scan and no approval is
requested.

## Notes

- Merging uses `GITHUB_TOKEN`. Do not require an approving PR *review* in
  branch protection, or the workflow's merge will be refused.
- A new push to the PR cancels the pending run and rescans; a cancelled run
  never closes the PR.
- The scan runs the gate script from the PR head; for untrusted contributors,
  check out the base branch's copy of `.github/scripts/` instead.
