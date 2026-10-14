# Demo: Semgrep scan + manual approval gate

Client-facing demo. Scans every pull request with Semgrep, reports the findings
on the PR, then waits for a human to approve (merge) or reject (close).

**No LLM, no auto-fix, no fix branch.** The earlier LLM autofix PoC is kept
untouched: git tag `poc-llm-autofix-v1`, branch `backup/llm-autofix-poc`, and
the archived workflow in `poc-archive/llm-autofix/`.

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

`Security gate` is the aggregate check: green when the scan is clean or a
reviewer approved, red while pending or rejected. Require this one check in
branch protection so the GitHub merge button stays blocked until a decision.

Only findings **new in the PR** are reported (`--baseline-commit` against the
PR base), at severity `WARNING` or higher (`MIN_SEVERITY` in the workflow).

## One-time setup

1. Make sure the workflow is on the branch your PRs target (this demo lives on
   `client-demo`; merge it into `main` when ready).
2. Create the approval environment with required reviewers:

   ```
   gh auth login
   scripts/setup-approval-environment.sh                       # you as reviewer
   scripts/setup-approval-environment.sh owner/repo alice bob  # explicit
   ```

   Or in the UI: Settings -> Environments -> New environment
   `security-approval` -> Required reviewers. (Private repos need a paid
   GitHub plan for required reviewers; public repos are free.)
3. Settings -> Branches -> branch protection for the target branch -> require
   status check **Security gate**.
4. Settings -> Actions -> General -> Workflow permissions: read and write.

If the environment has no reviewers the workflow fails closed: it posts
"approval environment is not configured" and the gate stays red, instead of
letting findings through unattended.

## Run the demo

```
git push -u origin demo/vulnerable-change
gh pr create --base client-demo --head demo/vulnerable-change \
  --title "Add user search" --body "Demo PR with a SQL injection"
```

`demo/vulnerable-change` reintroduces the original SQL injection (and the
`0.0.0.0` bind) in `app.py`. Then:

1. The **Semgrep scan** check fails and the PR gets a findings comment.
2. Open the workflow run -> **Review deployments** -> Approve or Reject.
3. Approve: the PR is merged. Reject: the PR is closed. Either way a comment
   records who decided.

To demo the clean path, open a PR with no security issues: scan is green,
no approval is requested.

## Notes

- Merging uses `GITHUB_TOKEN`; if branch protection requires an approving PR
  review, merging from the workflow will be refused. Use the "Security gate"
  check instead of required reviews, or allow the bot to bypass.
- A new push to the PR cancels the pending run and rescans; a cancelled run
  never closes the PR.
- Ruleset: `p/python`, `p/flask`, `p/security-audit` (no Semgrep login needed).
  Edit the `semgrep scan --config` flags in the workflow to change it.
- The scan runs the gate script from the PR head; for untrusted contributors,
  check out the base branch's copy of `.github/scripts/` instead.
