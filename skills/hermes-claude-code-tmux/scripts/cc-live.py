#!/usr/bin/env python3
"""Live-ish view of a running Claude Code session transcript.

Usage: cc-live.py <session_id_or_'latest'> [lines]

Renders the transcript JSONL (~/.claude/projects/<slug>/<id>.jsonl) as a compact
stream: assistant text, tool calls with their first argument, and tool results
truncated. Read-only; safe to run against a live run.
"""
import json
import os
import sys
import glob

proj_root = os.path.expanduser("~/.claude/projects")


def find(arg: str) -> str:
    if arg == "latest":
        files = glob.glob(os.path.join(proj_root, "*", "*.jsonl"))
        if not files:
            sys.exit("no transcripts found")
        return max(files, key=os.path.getmtime)
    if os.path.exists(arg):
        return arg
    hits = glob.glob(os.path.join(proj_root, "*", arg + "*.jsonl"))
    if not hits:
        sys.exit(f"no transcript matching {arg}")
    return max(hits, key=os.path.getmtime)


def brief(obj, n=160):
    if obj is None:
        return ""
    if isinstance(obj, str):
        s = obj
    else:
        s = json.dumps(obj, ensure_ascii=False)
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1] + "…"


def main():
    path = find(sys.argv[1] if len(sys.argv) > 1 else "latest")
    tail = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    print(f"# {path}")
    out = []
    with open(path, errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = ev.get("type")
            ts = (ev.get("timestamp") or "")[11:19]
            msg = ev.get("message") or {}
            content = msg.get("content")
            if t == "assistant" and isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "text" and block.get("text", "").strip():
                        out.append(f"{ts} CC  {brief(block['text'], 400)}")
                    elif block.get("type") == "tool_use":
                        args = block.get("input") or {}
                        arg = (
                            args.get("command")
                            or args.get("file_path")
                            or args.get("pattern")
                            or args.get("prompt")
                            or ""
                        )
                        out.append(f"{ts} ->  {block.get('name')}: {brief(arg, 200)}")
            elif t == "user" and isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        c = block.get("content")
                        if isinstance(c, list):
                            c = " ".join(
                                b.get("text", "") for b in c if isinstance(b, dict)
                            )
                        out.append(f"{ts} <-  {brief(c, 200)}")
    print("\n".join(out[-tail:]))


if __name__ == "__main__":
    main()
