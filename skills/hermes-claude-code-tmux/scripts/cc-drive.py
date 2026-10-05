#!/usr/bin/env python3
"""cc-drive.py — drive an INTERACTIVE Claude Code session in tmux.

Substrate: `claude` (TUI) inside a named detached tmux session, not `claude -p`.
Gives Hermes: multi-turn in one process, the ability to answer permission
dialogs and clarifying questions, and no print-mode background ceiling.

Reliability comes from hooks, not from scraping the TUI: a per-session
`--settings` file installs Stop / SessionStart / Notification hooks that touch
marker files under the session state dir.

Subcommands:
  start  <name> <workdir> [--model M] [-- <extra claude args>...]
  send   <name> <prompt_file>
  wait   <name> [timeout_s]        -> done | needs-input | dead | timeout
  state  <name>                    -> markers, dialog detection, pane tail
  answer <name> <choice_index>     -> navigate a permission dialog and confirm
  capture <name> [scrollback]
  stop   <name>

State dir: /tmp/cc-drive/<name>   (markers: started, turn-done, needs-input)
tmux session name: cc-<name>
"""
import os, shlex, subprocess, sys, time, json, re

STATE_ROOT = "/tmp/cc-drive"


def sh(*args, check=False):
    return subprocess.run(args, capture_output=True, text=True, check=check)


def tmux_name(name):
    return f"cc-{name}"


def state_dir(name):
    return os.path.join(STATE_ROOT, name)


def marker(name, which):
    return os.path.join(state_dir(name), which)


def capture(name, scrollback=None):
    args = ["tmux", "capture-pane", "-p", "-t", tmux_name(name)]
    if scrollback:
        args += ["-S", f"-{scrollback}"]
    r = sh(*args)
    return r.stdout


def pane_alive(name):
    r = sh("tmux", "list-panes", "-t", tmux_name(name), "-F", "#{pane_dead}")
    return r.returncode == 0 and r.stdout.strip() == "0"


def dialog_kind(pane):
    """Detect a blocking dialog from the pane text."""
    if re.search(r"Do you trust the files in this folder", pane):
        return "trust"
    if re.search(r"Do you want to proceed\?", pane) and re.search(r"❯\s*1\.", pane):
        return "permission"
    if re.search(r"Bypass permissions mode", pane):
        return "bypass-warning"
    return None


def write_settings(name):
    d = state_dir(name)
    hooks = {
        "SessionStart": [{"hooks": [{"type": "command", "command": f"touch {shlex.quote(marker(name,'started'))}"}]}],
        "Stop":         [{"hooks": [{"type": "command", "command": f"touch {shlex.quote(marker(name,'turn-done'))}"}]}],
        "Notification": [{"hooks": [{"type": "command", "command": f"touch {shlex.quote(marker(name,'needs-input'))}"}]}],
    }
    path = os.path.join(d, "settings.json")
    with open(path, "w") as f:
        json.dump({"hooks": hooks}, f, indent=2)
    return path


def cmd_start(argv):
    if len(argv) < 2:
        sys.exit("usage: start <name> <workdir> [--model M] [-- extra...]")
    name, workdir = argv[0], argv[1]
    rest = argv[2:]
    model = None
    extra = []
    if "--model" in rest:
        i = rest.index("--model"); model = rest[i + 1]; del rest[i:i + 2]
    if "--" in rest:
        i = rest.index("--"); extra = rest[i + 1:]; del rest[i:i + 1]
    os.makedirs(state_dir(name), exist_ok=True)
    for m in ("started", "turn-done", "needs-input"):
        try: os.remove(marker(name, m))
        except FileNotFoundError: pass
    settings = write_settings(name)
    cmd = ["claude", "--settings", settings]
    if model: cmd += ["--model", model]
    cmd += extra
    if sh("tmux", "has-session", "-t", tmux_name(name)).returncode == 0:
        sys.exit(f"tmux session {tmux_name(name)} already exists")
    line = " ".join(shlex.quote(c) for c in cmd)
    r = sh("tmux", "new-session", "-d", "-s", tmux_name(name),
           "-x", "220", "-y", "50", "-c", workdir, line)
    if r.returncode != 0:
        sys.exit(f"tmux new-session failed: {r.stderr.strip()}")
    sh("tmux", "set-option", "-t", tmux_name(name), "remain-on-exit", "on")
    # handle a first-run trust dialog, then wait for readiness
    deadline = time.time() + 25
    while time.time() < deadline:
        pane = capture(name)
        k = dialog_kind(pane)
        if k == "trust":
            sh("tmux", "send-keys", "-t", tmux_name(name), "Enter")
            time.sleep(1); continue
        if os.path.exists(marker(name, "started")) or re.search(r"^❯", pane, re.M):
            break
        time.sleep(1)
    print(f"started tmux={tmux_name(name)} state={state_dir(name)}")
    print(capture(name, scrollback=40).rstrip())


def cmd_send(argv):
    name, prompt_file = argv[0], argv[1]
    with open(prompt_file) as f:
        text = f.read()
    try: os.remove(marker(name, "turn-done"))
    except FileNotFoundError: pass
    with open(os.path.join(state_dir(name), "last-prompt.txt"), "w") as f:
        f.write(text)
    sh("tmux", "load-buffer", "-b", "ccp", prompt_file)
    sh("tmux", "paste-buffer", "-b", "ccp", "-t", tmux_name(name))
    time.sleep(0.8)
    sh("tmux", "send-keys", "-t", tmux_name(name), "Enter")
    time.sleep(1.5)
    # bracketed paste sometimes eats the first Enter: resend if still in the box
    pane = capture(name)
    first_line = " ".join(text.split())[:40]
    tail = "\n".join(pane.splitlines()[-25:])
    if first_line and first_line[:20] in tail and re.search(r"^❯\s+\S", tail, re.M):
        sh("tmux", "send-keys", "-t", tmux_name(name), "Enter")
    print("sent")


def cmd_wait(argv):
    name = argv[0]
    timeout = int(argv[1]) if len(argv) > 1 else 600
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not pane_alive(name):
            print("dead"); return
        pane = capture(name)
        k = dialog_kind(pane)
        if k and k != "trust":
            print(f"needs-input:{k}"); return
        if os.path.exists(marker(name, "turn-done")):
            print("done"); return
        time.sleep(2)
    print("timeout")


def cmd_state(argv):
    name = argv[0]
    print(f"tmux={tmux_name(name)} alive={pane_alive(name)}")
    for m in ("started", "turn-done", "needs-input"):
        p = marker(name, m)
        print(f"  {m}: {'yes' if os.path.exists(p) else 'no'}")
    pane = capture(name, scrollback=120)
    print(f"  dialog={dialog_kind(pane)}")
    print("--- pane tail ---")
    print("\n".join([l for l in pane.splitlines() if l.strip()][-25:]))


def cmd_answer(argv):
    name, idx = argv[0], int(argv[1])
    pane = capture(name)
    if dialog_kind(pane) != "permission":
        sys.exit("no permission dialog detected")
    cur = 1
    m = re.search(r"❯\s*(\d+)\.", pane)
    if m: cur = int(m.group(1))
    steps = idx - cur
    key = "Down" if steps > 0 else "Up"
    for _ in range(abs(steps)):
        sh("tmux", "send-keys", "-t", tmux_name(name), key); time.sleep(0.3)
    pane = capture(name)
    mm = re.search(r"❯\s*(\d+)\.(?:\s*(.*))?", pane)
    if not mm or int(mm.group(1)) != idx:
        sys.exit(f"could not land on option {idx}; pane shows {mm.group(0) if mm else '?'}")
    sh("tmux", "send-keys", "-t", tmux_name(name), "Enter")
    print(f"answered option {idx}: {mm.group(0).strip()}")


def cmd_capture(argv):
    name = argv[0]
    sb = int(argv[1]) if len(argv) > 1 else 120
    print(capture(name, scrollback=sb))


def cmd_stop(argv):
    name = argv[0]
    sh("tmux", "send-keys", "-t", tmux_name(name), "/exit"); time.sleep(0.4)
    sh("tmux", "send-keys", "-t", tmux_name(name), "Enter"); time.sleep(2)
    sh("tmux", "kill-session", "-t", tmux_name(name))
    print("stopped")


CMDS = {"start": cmd_start, "send": cmd_send, "wait": cmd_wait, "state": cmd_state,
        "answer": cmd_answer, "capture": cmd_capture, "stop": cmd_stop}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in CMDS:
        sys.exit(__doc__)
    CMDS[sys.argv[1]](sys.argv[2:])