#!/usr/bin/env bash
# PreToolUse hook for Bash. Probes gpg-agent's passphrase cache before any
# git command that could create a signed commit/tag. If the cache is cold,
# blocks the command so Claude Code's TTY does not hang on pinentry.
set -u

input=$(cat)
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // ""' 2>/dev/null)
[ -z "$cmd" ] && exit 0

case "$cmd" in
  *"git commit"*|*"git tag"*|*"git merge"*|*"git cherry-pick"*|*"git revert"*|*"git rebase"*) ;;
  *) exit 0 ;;
esac

if printf '%s' "$cmd" | grep -qE -- '--no-gpg-sign|commit\.gpgsign=false|gpg\.format=ssh'; then
  exit 0
fi

key=$(git config --global --get user.signingkey 2>/dev/null)
[ -z "$key" ] && exit 0

if echo "" | timeout 3 gpg --batch --no-tty --sign --local-user "$key" >/dev/null 2>&1; then
  exit 0
fi

cat <<'EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "GPG passphrase cache is cold; signing this commit would hang Claude Code's TTY because pinentry cannot prompt from inside a CC session. Tell the user to pre-unlock the key in a normal (non-CC) terminal: `echo test | gpg --clearsign > /dev/null` — the cache then stays warm for 24h. Do NOT auto-fallback to --no-gpg-sign without explicit user authorization for this specific commit."
  }
}
EOF
exit 0
