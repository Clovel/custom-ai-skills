#!/usr/bin/env python3
"""Trust every git repository under a root for Claude Code, one entry per repo path.

WHY per path: Claude Code resolves project trust per exact directory. A trust entry on a
parent directory does NOT cover a clone inside it -- `/home/u`, `/home/u/repository` and
`/home/u/repository/<client>` trusted all still print "this workspace has not been trusted"
for `/home/u/repository/<client>/<repo>`. Subdirectories *inside* a trusted repo are covered,
and so is a git worktree of that repo, so one entry per clone suffices; a submodule directory
is its own git root and needs its own, as does a worktree checked out at a new path.

Without the entry, the repo's committed .claude/settings.json (permissions, hooks) is silently
ignored, and a headless run has to have every tool granted on the command line instead.

Usage:
    scripts/trust_cloned_repos.py [root ...]      # default: ~/repository
    scripts/trust_cloned_repos.py --dry-run ~/repository

Run it while no Claude Code session is in flight: the CLI rewrites ~/.claude.json as it exits,
so an edit made during a run can be lost (re-run and re-read the file afterwards if unsure).
"""

import json
import os
import shutil
import sys
import time

CONFIG = os.path.expanduser("~/.claude.json")
SKIP = {"node_modules", ".cache", "dist", "build", "venv", ".venv", "target"}
MAX_DEPTH = 4


def discover(roots):
    repos = []
    for root in roots:
        root = os.path.abspath(os.path.expanduser(root))
        for current, dirnames, _ in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP and not d.startswith(".")]
            rel = os.path.relpath(current, root)
            if rel != "." and rel.count(os.sep) + 1 > MAX_DEPTH:
                dirnames[:] = []
                continue
            if os.path.exists(os.path.join(current, ".git")):  # dir, or file for worktree/submodule
                repos.append(current)
    return sorted(set(repos))


def main():
    argv = sys.argv[1:]
    dry_run = "--dry-run" in argv
    roots = [a for a in argv if not a.startswith("--")] or ["~/repository"]

    repos = discover(roots)
    if not repos:
        raise SystemExit(f"no git repository found under {roots}")

    with open(CONFIG) as handle:
        config = json.load(handle)

    projects = config.setdefault("projects", {})
    todo = [p for p in repos if projects.get(p, {}).get("hasTrustDialogAccepted") is not True]

    print(f"{len(repos)} repositories found, {len(todo)} to trust")
    for path in todo:
        print("  +", path)
    if dry_run:
        return
    if not todo:
        print("nothing to write")
        return

    backups = os.path.expanduser("~/.claude/backups")
    os.makedirs(backups, exist_ok=True)
    backup = os.path.join(backups, f"claude.json.pre-trust-{time.strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(CONFIG, backup)
    print("backup:", backup)

    for path in todo:
        projects.setdefault(path, {})["hasTrustDialogAccepted"] = True

    tmp = CONFIG + ".tmp"
    with open(tmp, "w") as handle:
        json.dump(config, handle, indent=2)
    os.replace(tmp, CONFIG)  # atomic: a truncated config breaks every future session
    os.chmod(CONFIG, 0o600)

    with open(CONFIG) as handle:
        written = json.load(handle)
    missing = [
        p for p in todo if written["projects"].get(p, {}).get("hasTrustDialogAccepted") is not True
    ]
    print("verify:", "OK" if not missing else f"FAILED for {missing}")
    if missing:
        sys.exit(1)


if __name__ == "__main__":
    main()
