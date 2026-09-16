---
name: hermes-code-delegation
description: Routes all codebase work to the Claude Code CLI instead of the agent's own file tools, and picks the model the task warrants. Use whenever a request involves reading, searching, analysing, reviewing, explaining, debugging, testing, refactoring, or changing code in a repository — "review this MR", "review this branch", "why is this test failing", "how does auth work here", "add an endpoint", "fix this bug", "write tests for", "explain this function", "clean up this module", "look at this project", "what does this code do". Applies BEFORE opening any file inside a repository, not after.
---

# hermes-code-delegation

**Codebase work goes to Claude Code. Not to this agent's own file tools.**

Read this before the first file you open inside a repository — the decision this skill
governs is made at that moment, and it cannot be unmade afterwards.

## Why

Two reasons, and the first is the one that bites quietly.

**Reading a codebase with your own tools bills every byte to your own model provider.**
Forty files read is forty files of context, metered, and most of it is never used
again. Delegating sends the reading to a harness billed separately — typically a flat
subscription rather than per-token — and what comes back is a paragraph. The work
moves; the token cost mostly disappears rather than relocating.

This is the difference between a task costing a few hundred tokens and a task costing a
hundred thousand. An agent that analyses codebases directly will exhaust a daily quota
on a single afternoon's work, and the failure looks like an unrelated outage later.

**Second: a code-specialised harness is simply better at it.** It has the file
navigation, the diff handling, the test loop and the model tiering already built. Doing
it by hand with generic read and write tools produces worse results more slowly.

## What counts

| Do it yourself | Delegate |
| --- | --- |
| `git log`, `git status`, branch and tag names | Reading a diff in order to **judge** it |
| Your own configuration, memory and notes | Anything inside a repository working tree |
| One file, to answer one direct question about it | Anything spanning more than a file or two |
| A snippet someone pasted into the conversation | Any edit to a tracked file, ever |
| Reporting what a delegated run concluded | Searching a repository to find something |

The boundary that matters: **if the answer requires looking at code you have not
already been given, delegate.** Opening "just one more file" to check something is how
a delegated task becomes an undelegated one.

## Choosing the model

Pass `--model`. The task's difficulty decides, not its length.

The top two tiers differ by the **shape** of the task, not by which is stronger — one
goes deep in a bounded area, the other goes wide across a whole tree.

| Tier | Use for | `--model` |
| --- | --- | --- |
| Cheap | Mechanical and bounded: "where is X defined", renames, formatting, generated boilerplate, a single obvious fix | `haiku` |
| Default | Most real work: implementing a feature, fixing a bug, writing tests, reviewing a diff, explaining a module | `sonnet` |
| Deep | Hard reasoning in a known place: a subtle or security-relevant bug, a tricky algorithm, a design decision with expensive consequences | `opus` |
| Broad | Work that spans the codebase: a feature touching many modules, a review of a whole tree rather than a diff, a large refactor, a long autonomous run | `fable` |

Aliases select the current model in each tier; full identifiers also work when a
specific one is required.

**Default to `sonnet` when unsure.** Under-modelling a hard task does not fail loudly —
it returns confident, wrong code that costs far more to find and undo than the tokens it
saved. Reserve `haiku` for tasks whose correctness you could verify at a glance.

**Choose the top tier by shape.** "This bug is subtle and I know roughly where it is"
is `opus`. "This change touches things I have not found yet" is `fable`, which is built
for whole-codebase work and long-horizon runs, and whose cache reads are cheap enough
that a long session is not punished for re-reading context.

Escalate rather than retry: if a run comes back confused, contradictory, or having
misread the structure of the code, re-run at a higher tier with the same prompt rather
than repeating it. If it misread the *structure* specifically, that is a breadth
failure — go to `fable`, not `opus`.

## Reviewing code

Review is delegation like anything else — the criteria go in the prompt, not into your
own reading of the diff. A review prompt should ask for:

- Type safety and error handling
- Edge cases, and what happens on the unhappy path
- Security-relevant changes
- Whether tests actually cover what changed
- Breaking changes, called out explicitly

Reviewing a diff is `sonnet` work. Reviewing a whole codebase, or a change whose
consequences are not confined to the lines it touches, is `fable` work.

Then report the findings. Do not re-read the diff yourself to check the review; if the
review is not trustworthy, re-run it a tier up.

## How to dispatch

Mechanics — sessions, polling, collecting output, resuming — are not repeated here.
Follow the `hermes-claude-code-tmux` skill, which is the authority on how a run is
started and retrieved. In short: a named detached session, never a blocking foreground
call.

Write the prompt as a brief, not an instruction to a file editor. State the goal, the
constraints, and what a good answer looks like. A delegated run has its own context and
its own tools; it does not need the files listed for it, and listing them usually
narrows the work incorrectly.

## When not to delegate

The rule has a floor. Do not spawn a run to read a single short file that has already
been named, to answer a question about code that is already quoted in the conversation,
or to check something a shell command answers outright (whether a file exists, what a
branch is called, what a command's help output says). A delegated run has a fixed
overhead in time and coordination; below a certain size, doing it directly is both
cheaper and faster.

The test is whether the work involves *exploring* code. Exploration delegates. Lookups
of a known thing do not.
