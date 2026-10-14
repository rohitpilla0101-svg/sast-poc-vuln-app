#!/usr/bin/env bash
# One-time setup for the Semgrep approval gate: creates the `security-approval`
# environment with required reviewers. Without reviewers GitHub would let the
# approval job through unattended (the workflow refuses to rely on that).
#
# Usage: scripts/setup-approval-environment.sh [owner/repo] [reviewer-login ...]
# Defaults: current repo (via gh), and the logged-in user as the only reviewer.
# Needs: gh CLI, authenticated with admin rights on the repo.
set -euo pipefail

REPO="${1:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}"
shift || true
REVIEWERS=("$@")
if [ "${#REVIEWERS[@]}" -eq 0 ]; then REVIEWERS=("$(gh api user -q .login)"); fi
ENV_NAME="security-approval"

reviewers_json=""
for login in "${REVIEWERS[@]}"; do
  id="$(gh api "users/$login" -q .id)"
  reviewers_json+="${reviewers_json:+,}{\"type\":\"User\",\"id\":$id}"
done

# prevent_self_review=false so one person can play author and approver in a
# demo; set it to true for a real four-eyes policy.
gh api --method PUT "repos/$REPO/environments/$ENV_NAME" --input - <<JSON
{"reviewers":[$reviewers_json],"prevent_self_review":false}
JSON

echo "Environment '$ENV_NAME' on $REPO now requires approval from: ${REVIEWERS[*]}"
