#!/usr/bin/env bash
# gpg-rewarm — re-warm gpg-agent's passphrase cache for a specific key,
# resetting its TTL window even if the cache has NOT expired yet.
#
# Why this exists: re-running a plain `gpg --clearsign` while the cache is
# still valid does NOT extend the lifetime — `max-cache-ttl` is measured from
# the first unlock and is never bumped by use. To force a fresh window you must
# flush the cached passphrase first, then re-sign to trigger pinentry. And since
# a bare `--clearsign` signs with the DEFAULT key, you must pin the key with -u
# or you warm the wrong key's cache.
#
# Run in a normal terminal — pinentry cannot prompt inside a non-interactive TTY.
#
# Usage: gpg-rewarm <keyid|fingerprint|email>
# Install: source this file from ~/.bashrc or ~/.zshrc, or run it directly.

gpg-rewarm() {
  local keyid="$1"
  [ -z "$keyid" ] && { echo "usage: gpg-rewarm <keyid|fpr|email>" >&2; return 1; }

  # Collect every signing-capable keygrip for this key (primary + signing subkeys).
  # Field 12 of sec/ssb holds capabilities (lowercase s = this key can sign);
  # field 10 of the following grp record is the keygrip.
  local grips
  grips=$(gpg --with-colons --with-keygrip --list-secret-keys "$keyid" 2>/dev/null \
    | awk -F: '
        $1=="sec" || $1=="ssb" { sign = index($12, "s") }
        $1=="grp" && sign      { print $10 }
      ')
  [ -z "$grips" ] && { echo "gpg-rewarm: no signing key found for '$keyid'" >&2; return 1; }

  # Flush each signing keygrip's cached passphrase. Flushing extras is harmless;
  # the single warm signature below only re-caches whichever key gpg actually uses.
  local g
  while IFS= read -r g; do
    [ -n "$g" ] && gpg-connect-agent "clear_passphrase --mode=normal $g" /bye >/dev/null
  done <<< "$grips"

  # Force a fresh signature so pinentry re-caches for a full new window.
  # -u pins the (possibly non-default) key so the RIGHT cache is warmed.
  echo test | gpg -u "$keyid" --clearsign >/dev/null \
    && echo "gpg-rewarm: re-warmed '$keyid'"
}

# Allow running the file directly, not only sourcing it.
if [ "${BASH_SOURCE[0]:-}" = "$0" ]; then
  gpg-rewarm "$@"
fi
