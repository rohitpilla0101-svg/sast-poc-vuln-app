# Archived: environment-based approval variant

Same Semgrep gate, but the pause is a GitHub Environment with required
reviewers (a "Review deployments" button on the run page). Required reviewers
on a **private** repo need a paid GitHub plan (Pro/Team/Enterprise), so the
active demo uses PR reviews instead. To use this variant on a paid plan:

1. Copy `semgrep-approval-gate.yml.disabled` over
   `.github/workflows/semgrep-approval-gate.yml` and delete
   `.github/workflows/semgrep-decision.yml`.
2. Restore the `report`/`decide` handling for approvals in
   `.github/scripts/semgrep_gate.py` from git history (commit
   "feat: Semgrep PR gate with manual approval demo").
3. Run `setup-approval-environment.sh` to create the `security-approval`
   environment with reviewers.
