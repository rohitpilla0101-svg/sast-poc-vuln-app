# Archived: LLM autofix PoC

`sast-autofix.yml.disabled` is the original workflow (self-hosted runner,
Laya + Ollama triage, `<branch>-fix` PR). It is parked here so it does not
run alongside the approval-gate demo. To revive it, move it back to
`.github/workflows/sast-autofix.yml` (and remove the Semgrep gate workflow),
or check out the tag `poc-llm-autofix-v1` / branch `backup/llm-autofix-poc`.
