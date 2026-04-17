# custom-ai-skills

A collection of custom SKILL.md skills for Claude Code and any agent that
supports the [Agent Skills](https://github.com/anthropics/skills) spec.

Each skill lives under `skills/<name>/SKILL.md` and is installable
individually or as a set via the [`skills` CLI](https://skills.sh).

## Skills

### [`refine-qa-notes`](./skills/refine-qa-notes)

Generates a structured QA tracking document from raw QA session notes.
Takes a quickly-written, potentially multilingual markdown or plain-text
notes file and produces an English markdown document with an issue summary
table (status, priority, size) and per-issue analysis sections, designed to
be updated by humans or AI agents as fixes land.

```bash
npx skills add Clovel/custom-ai-skills --skill refine-qa-notes
```

## Install everything

```bash
npx skills add Clovel/custom-ai-skills
```

## Usage

Skills activate automatically based on their `description` frontmatter
field. In Claude Code, typing `/` lists available skills and lets you
invoke one explicitly.

## Updating

```bash
npx skills list      # show installed skills
npx skills update    # update all installed skills
```

## Contributing

Issues and pull requests are welcome. New skills should follow the existing
`skills/<name>/SKILL.md` layout and include valid YAML frontmatter. See
[AGENTS.md](./AGENTS.md) for conventions.

## License

[MIT](./LICENSE).
