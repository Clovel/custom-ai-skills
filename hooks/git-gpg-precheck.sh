#!/usr/bin/env bash
# PreToolUse hook for Bash. Probes gpg-agent's passphrase cache before any
# git command that could create a signed commit/tag. If the cache is cold,
# blocks the command so Claude Code's TTY does not hang on pinentry.
set -u

input=$(cat)
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // ""' 2>/dev/null)
[ -z "$cmd" ] && exit 0

# Bail unless this is a git operation that may produce a signed commit/tag.
# The keyword check tolerates flags between `git` and the subcommand
# (e.g. `git -C /repo commit`, `git -c key=val tag`).
if ! printf '%s' "$cmd" | grep -qE '\bgit\b' \
   || ! printf '%s' "$cmd" | grep -qE '\b(commit|tag|merge|cherry-pick|revert|rebase)\b'; then
  exit 0
fi

if printf '%s' "$cmd" | grep -qE -- '--no-gpg-sign|commit\.gpgsign=false|gpg\.format=ssh'; then
  exit 0
fi

# Determine the target repo dir so we read the right signingkey. A repo's
# local .git/config can override the global signingkey (e.g. a personal key
# in a personal repo), so probing the global key would give false positives.
work_dir="$PWD"
extracted=$(printf '%s' "$cmd" | grep -oE 'git[[:space:]]+-C[[:space:]]+[^[:space:]]+' | head -1 | sed -E 's/^git[[:space:]]+-C[[:space:]]+//')
[ -n "$extracted" ] && work_dir="$extracted"

# Resolve signing key with local > global precedence. Empty = no signing
# configured = nothing to enforce.
key=$(git -C "$work_dir" config --get user.signingkey 2>/dev/null)
[ -z "$key" ] && key=$(git config --global --get user.signingkey 2>/dev/null)
[ -z "$key" ] && exit 0

# Probe: succeeds quickly if the agent has THIS key cached, fails fast if cold.
if echo "" | timeout 3 gpg --batch --no-tty --sign --local-user "$key" >/dev/null 2>&1; then
  exit 0
fi

cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "GPG passphrase cache is cold for signing key ${key}; signing this commit would hang Claude Code's TTY because pinentry cannot prompt from inside a CC session. Tell the user to pre-unlock the key in a normal (non-CC) terminal: \`echo test | gpg --clearsign --local-user ${key} > /dev/null\` — the cache then stays warm for 24h. Do NOT auto-fallback to --no-gpg-sign without explicit user authorization for this specific commit."
  }
}
EOF
exit 0
