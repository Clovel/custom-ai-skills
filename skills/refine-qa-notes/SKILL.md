---
name: refine-qa-notes
description: Use this skill whenever the user has raw QA session notes (markdown, plain text, often multilingual, unorganized) and wants to turn them into a structured tracking document for follow-up work. Trigger on phrases like "refine these QA notes", "turn my QA session into a tracking doc", "organize this bug list", "write a QA followup document", or when the user pastes rough QA notes and asks for anything resembling a plan, recap, or remediation document. Also trigger when the user wants a living document to track QA corrections (TODO/WIP/DONE), prepare QA output for developers or AI agents to work through, or produce an artifact the QA team can later use to validate fixes.
---

# Refine QA Notes

Turn raw QA session notes into a structured, living tracking document that humans and AI agents can work from end-to-end — from picking issues, to fixing them, to validating the fixes.

## Why this skill exists

QA sessions produce messy output: bullet points typed quickly, multiple languages, incomplete sentences, no clear prioritization, sometimes the same bug described twice in different places. That raw output is hard to act on, and rewriting it by hand after every session is tedious.

The output document this skill produces is a single English markdown file that serves three audiences at different points in time:

1. **Developers or AI agents** who need to pick an issue, analyze it, and fix it.
2. **Anyone tracking progress** — the document itself is the source of truth for TODO / WIP / DONE.
3. **The QA team later**, validating that the fixes landed and match what they originally reported.

Keeping all three concerns in one document avoids drift between a ticket tracker, a chat log, and a spreadsheet.

## Input

The user provides raw QA notes, usually as a markdown or plain-text blob pasted inline or attached as a file. Expect:

- Mixed languages (commonly French + English, but don't assume)
- Abbreviations, typos, and shorthand
- Missing context (e.g. "login broken on mobile" with no browser/device info)
- No consistent severity labeling
- Occasional duplicates or near-duplicates

Read the full input before writing anything. Look for implicit grouping — QA notes often follow the session's flow (login → onboarding → dashboard → settings), and preserving that flow in the output makes it easier to navigate.

## Ground the analysis in the app's business logic

Before writing the output, skim whatever project context is available — `CLAUDE.md`, `README.md`, architecture docs, onboarding notes, recent changelog, domain glossaries — so the Analysis sections can speak to what the app actually does rather than producing generic guesses. Business-logic grounding sharpens three things: priority inference (is this a hot path or a rarely-used admin screen?), size estimation (is this area tangled or cleanly isolated?), and the quality of the probable-cause hints handed to whoever picks up the issue.

When no project context is accessible (e.g. the skill is running against pasted notes with no repo attached), say so in the Introduction — "Analysis below is based on the QA notes alone; no codebase context was available" — and keep the Analysis sections appropriately conservative. Lean on what the note explicitly says, flag what needs verification, and don't invent causes.

## Output

A single markdown document, **always in English** regardless of the input language. English is the canonical output so downstream tooling, AI agents, and mixed-language teams can process it consistently. When a specific phrase from the original matters (a user-facing error message, a client's exact wording), keep it in the original language in quotes alongside the English rendering — don't silently translate literal quotes.

### Filename and dating

Save the output as `qa-session-refined-YYYYMMDD.md`. The date in the filename is the **QA session date** — i.e. when the notes were taken, not when this document is generated. If the session date isn't stated or inferable from the input, fall back to today's date and note the fallback in the Introduction ("Session date not specified; filename uses document generation date.").

The same date must appear in the top-level heading (see structure below), so the filename and the document always agree.

### Top-level structure

```
# QA Tracking — <YYYY-MM-DD>[ — <session name or project if known>]

## Introduction
<2–4 sentences: what was tested, when, by whom if known, high-level outcome>

## Summary of issues
<markdown table, see below>

## Issues
<one subsection per issue, see below>
```

### Summary-of-issues table

Use exactly these columns:

| #      | Description | Status | Priority | Size | Tracker |
| ------ | ----------- | ------ | -------- | ---- | ------- |
| QA-001 | <one line>  | TODO   | P1       | S    | —       |

Column rules:

- **#** — Stable prefix-number like `QA-001`, `QA-002`, zero-padded to three digits, so issues can be referenced in commits, PRs, and tickets.
- **Description** — One line. The shortest phrase that uniquely identifies the issue inside this document.
- **Status** — `TODO`, `WIP`, or `DONE`. Default to `TODO` on creation.
- **Priority** — `P0` (blocker / data loss / security), `P1` (major user-facing bug), `P2` (noticeable but not blocking), `P3` (polish / nice-to-have). Infer from the note's tone and what breaks: words like "cannot", "crashes", "lost my data" push toward P0/P1; "looks weird", "minor", "cosmetic" push toward P2/P3. When it's genuinely ambiguous, pick the higher priority and flag the uncertainty in the Analysis section.
- **Size** — `XS` (< 30 min, copy/typo/config), `S` (< 2h, single-file fix), `M` (half day, a few files), `L` (1–2 days, cross-cutting), `XL` (multi-day, needs design or refactor). If the note is too vague to estimate, append `?` (e.g. `M?`) rather than guessing confidently.
- **Tracker** — Optional Linear / GitLab / GitHub issue ID if one exists (e.g. `LIN-1234`). Leave `—` otherwise. This column is the bridge between this document and the team's real issue tracker.

If there are more than ~10 issues, split the table into logical sections (by area: *Auth*, *Dashboard*, *Settings*; or by severity tier: *Blockers*, *Major*, *Minor*). Pick the grouping that makes the table easiest to scan for the next person opening the document.

### Per-issue sections

Each issue gets its own subsection under `## Issues`, in this shape:

```
### QA-001 — <same one-line description as in the table>

**Status:** TODO | WIP | DONE
**Priority:** P1
**Size:** S
**Tracker:** LIN-1234 (or —)

#### Original note
> <verbatim quote from the QA notes, in the original language>

#### Analysis
<2–5 sentences: what the note probably means, likely reproduction steps,
probable cause area, related files/components if obvious, and any
ambiguity that needs clarification before a fix can be attempted>

#### Suggested fix (optional)
<only include when the fix is reasonably obvious from the note alone>

#### Applied fix
<empty until the issue is resolved; then: short summary of what was
done, plus commit SHA and/or PR link>
```

The **Original note** block is non-negotiable — it preserves the QA reporter's exact wording, which often contains subtleties an English paraphrase would lose. Keep it even when translating.

The **Analysis** is the main value-add of this skill. QA notes are terse; the analysis is where the skill connects dots: infers likely reproduction steps, flags missing info, points toward the part of the codebase that probably needs to change. Keep it tight — this is a briefing for the person picking up the issue, not a root-cause investigation. If deeper investigation is needed before the issue can even be scoped, say so explicitly in the Analysis ("needs reproduction before size can be estimated") so the picker knows to start there. Downstream agents with access to deeper analysis skills (Superpowers, codebase search, etc.) can do that second-pass work from this starting point.

## Handling ambiguity

QA notes are incomplete by nature. Apply these rules:

- **Duplicates:** When two notes clearly describe the same bug, merge them into one issue and quote both original lines inside the Original note block.
- **Near-duplicates:** When related but distinct (e.g. same bug in two different screens), create separate issues and cross-reference them in Analysis.
- **Unintelligible entries:** Don't invent detail. Create the issue with `Priority: P2`, `Size: ?`, and write "Original note is ambiguous; needs clarification from reporter" in Analysis.
- **Non-issues:** Positive comments like "overall looks great" or "love the new UI" don't become issues. Mention them briefly in the Introduction instead.

## Non-goals

This skill **does not**:

- Fix issues or write code patches
- Create tickets in Linear / GitLab / GitHub (only references them if already provided)
- Run the QA session itself or drive a browser
- Long-term maintain the document — subsequent updates (status changes, Applied fix summaries) are done by whoever takes the ticket, editing the same file in place

Keeping scope narrow makes the output predictable and the skill easy to chain with others (e.g. a downstream issue-picker skill, or a direct human workflow).

## Mini example

**Input (raw QA notes, mixed FR/EN):**

```
- login ok mais le bouton "mot de passe oublié" renvoie une 500
- dashboard : graphique des ventes vide sur mobile (iphone safari)
- typo "recieve" au lieu de "receive" dans l'email de confirmation
- ça rame énormément sur la page /reports quand on a + de 100 lignes
```

**Output fragment:**

```
## Summary of issues

| #      | Description                            | Status | Priority | Size | Tracker |
| ------ | -------------------------------------- | ------ | -------- | ---- | ------- |
| QA-001 | "Forgot password" endpoint returns 500 | TODO   | P0       | S?   | —       |
| QA-002 | Sales chart empty on mobile Safari     | TODO   | P1       | M    | —       |
| QA-003 | Typo "recieve" in confirmation email   | TODO   | P3       | XS   | —       |
| QA-004 | /reports slow with 100+ rows           | TODO   | P2       | M    | —       |

## Issues

### QA-001 — "Forgot password" endpoint returns 500

**Status:** TODO
**Priority:** P0
**Size:** S?
**Tracker:** —

#### Original note
> login ok mais le bouton "mot de passe oublié" renvoie une 500

#### Analysis
Login itself works, but clicking "Forgot password" hits a server
error. Blocker for any locked-out user, hence P0. Most likely a
backend problem on the password-reset route — start by checking
recent changes to that handler and its dependencies (SMTP config,
token generation, env vars). Size marked S? because the root cause
(missing env var vs. broken SMTP vs. logic bug) drives the real
effort.

#### Applied fix
—
```

The remaining issues follow the same pattern.
