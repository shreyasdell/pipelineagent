#!/bin/bash
# =============================================================================
# postCreateCommand — runs once after the dev container is created.
# Reference: https://containers.dev/implementors/json_reference/#lifecycle-scripts
#
# Runs as `vscode`. Only the CA step elevates, so the workspace and npm cache
# stay owned by the runtime user.
# =============================================================================
set -euo pipefail

# Resolve the repo root from this script's own path (.devcontainer/scripts/),
# so the script is portable across forks, renames, and manual invocation.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"
echo "[postCreate] Workspace: ${REPO_ROOT}"

# -----------------------------------------------------------------------------
# Corporate TLS interception — install the proxy root CA if one is in the path.
# No-ops on a clean network. Must precede anything that clones or fetches.
# -----------------------------------------------------------------------------
echo "[postCreate] Checking for corporate TLS interception..."
sudo -E sh "${SCRIPT_DIR}/install-corp-ca.sh"

# -----------------------------------------------------------------------------
# Matt Pocock skills — install selected engineering skills
#
# `skills` writes one canonical copy per skill into .agents/skills/ and then
# symlinks it into each *selected* agent's directory. Passing --agent claude-code
# is what creates .claude/skills/. Targeting `codex` (an AGENTS.md-standard
# "universal" agent) writes .agents/skills/ only, with no .claude/ mirror.
#
# `npx --yes` suppresses npx's own "Ok to proceed?" prompt — distinct from the
# `--yes` passed to `skills`. Without it this hangs, as there's no TTY here.
# -----------------------------------------------------------------------------
echo "[postCreate] Installing mattpocock/skills into .agents/ ..."
npx --yes skills add https://github.com/mattpocock/skills \
  --agent codex \
  --skill setup-matt-pocock-skills \
  --skill grill-with-docs \
  --skill to-spec \
  --skill to-tickets \
  --skill tdd \
  --skill code-review \
  --skill implement \
  --skill triage \
  --yes

# Defensive: if a future version mirrors into .claude/skills anyway, drop the
# symlinks. Only ever removes links, never the canonical .agents copy.
if [ -d .claude/skills ]; then
  echo "[postCreate] Removing .claude/skills mirror (canonical copy stays in .agents/)..."
  find .claude/skills -maxdepth 1 -type l -delete
  rmdir --ignore-fail-on-non-empty .claude/skills .claude 2>/dev/null || true
fi

echo "[postCreate] Skills installed:"
ls -1 .agents/skills 2>/dev/null || echo "  (none found — check the install output above)"

# -----------------------------------------------------------------------------
# Add further setup steps below, e.g.:
#
#   echo "[postCreate] Installing dependencies..."
#   npm ci
#
#   echo "[postCreate] Setting up Python environment..."
#   pip install -r requirements.txt --break-system-packages
# -----------------------------------------------------------------------------

echo "[postCreate] Done."
echo ""
echo "┌─────────────────────────────────────────────────────────────┐"
echo "│  First time using this repo?                                │"
echo "│  1. Run 'devin setup' to authenticate the Devin CLI         │"
echo "│  2. In Devin, run skill: /setup-matt-pocock-skills          │"
echo "└─────────────────────────────────────────────────────────────┘"