# AGENTS.md

Context for AI coding agents working in this repository. This is the
canonical source of truth; `CLAUDE.md` and any future agent-specific files
should point here.

## Purpose

This repo hosts a public collection of custom Agent Skills, distributed via
the [`skills` CLI](https://skills.sh). Skills in this repo are intended to
be consumable by Claude Code and any other agent runtime that implements
the Agent Skills spec.

## Directory layout

```
.
├── AGENTS.md
├── CLAUDE.md
├── LICENSE
├── README.md
└── skills/
    └── <skill-name>/
        ├── SKILL.md
        └── references/         # optional: bulky reference material
```

Every skill lives in its own directory under `skills/`. The entry file
**must** be named `SKILL.md` (uppercase) — the `skills` CLI discovers
skills by scanning for that exact filename.

## Adding a new skill

1. Create `skills/<skill-name>/`.
2. Write `skills/<skill-name>/SKILL.md` with valid YAML frontmatter:

   ```markdown
   ---
   name: <skill-name>
   description: <one-line description with trigger phrases>
   ---

   # <skill-name>

   <body>
   ```

3. Follow the authoring best practices from Anthropic's
   [skill-creator](https://github.com/anthropics/skills/tree/main/skill-creator).

## Conventions

- **Directory name matches frontmatter `name:`.** The `skills` CLI and
  most agents use the directory name as the canonical identifier; a
  mismatch with the `name:` field causes confusing activation bugs.
- **Descriptions must be pushy about triggers.** Claude tends to
  under-trigger skills, so enumerate the phrasings a user might actually
  type ("refine QA notes", "turn these QA notes into a doc", "create a QA
  tracking document from …"). One-line descriptions that only state what
  the skill *does* leave too much to inference.
- **Keep `SKILL.md` under ~500 lines.** The whole file is loaded into the
  agent's context on activation; anything longer bloats every session.
- **Move bulky material into `references/`.** Long examples, schemas, or
  prompt templates go in `skills/<skill-name>/references/` and are read on
  demand.

## Public-repo hard rules

This repo is public. Before committing, verify that no file contains:

- API keys, tokens, or any other credentials.
- Client names, project codenames, or internal product identifiers.
- Company-specific file paths, hostnames, or internal URLs.
- Proprietary business logic or strategy that isn't meant to be public.

If a skill was prototyped against a private project, scrub it before
moving it here.

## Testing a skill

A skill is considered validated when it activates and produces a useful
result for **2–3 realistic prompts** a user would actually type. Write
those prompts out before you commit, run them in a real agent session,
and confirm the skill both triggers on the description and behaves
correctly. For deeper evaluation tooling, see the
[skill-creator](https://github.com/anthropics/skills/tree/main/skill-creator)
skill.
