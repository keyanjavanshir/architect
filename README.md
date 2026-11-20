# agent-architect

An agent skill that **interviews you about a workflow, then builds the multi-agent system
to run it**: worker agents, the skills they need, an orchestrator that dispatches them in
parallel, and the MCP setup, all in the formats of the harness you use.

It works in **Claude Code, GitHub Copilot CLI, OpenAI Codex, Gemini CLI, Cursor and
OpenCode**. Copilot CLI's `/fleet` picks up the generated agents. In the others, the
orchestrator skill tells the main agent which sub-agents to spawn.

```
 you ──► interview ──► blueprint.yaml ──► render.py ──► agents + skills + orchestrator
          (grilling)    (one source,       (per harness)     + SETUP.md (MCP, secrets)
                         any harness)            │
                                                 └──► validate.py (size, safety, format)
```

## Why

Writing a good agent team by hand means getting a lot of small things right: descriptions
that trigger correctly, prompts that work without the main agent's context, tools scoped
per agent, parallel workers that never write the same file, credentials kept out of files.
On top of that, every harness uses its own file format. agent-architect handles this:

- **Interviews first.** It walks a design tree one question at a time, recommends an answer
  for each, and reads your repo instead of asking things it can look up. It checks whether
  you need a multi-agent system at all; often one skill, `/batch` or `/fleet` is enough.
- **Reuses what exists.** It searches the official MCP registry and existing skills before
  generating anything new.
- **Keeps generated files small.** Short entry files with reference files loaded on demand.
  The size limits are enforced by a validator, not left to the model.
- **Safe by default.** Least-privilege tools, file ownership checks for parallel agents,
  human checkpoints before irreversible actions, secrets only as `${VAR}` references, and
  MCP servers proposed with exact config snippets but never installed without your yes.
- **One blueprint, six harnesses.** The design is harness-neutral YAML. A deterministic
  renderer writes each harness's files, so switching or adding a harness is one command.

## Install

With the [skills CLI](https://github.com/vercel-labs/skills) (any harness):

```bash
npx skills add <owner>/agent-architect --skill agent-architect
```

Or clone and run the installer. It installs for your user by default; pass `--project` to
install into the current repo:

```bash
git clone https://github.com/<owner>/agent-architect
./agent-architect/install.sh            # ~/.agents/skills + ~/.claude/skills link
./agent-architect/install.sh --project  # ./.agents/skills + ./.claude/skills link
```

Requirements: Python 3.11+ and PyYAML (`pip install pyyaml`) for the scripts.

## Use

Start your harness in the project where the system should live and say something like:

> /agent-architect I want a workflow that triages new GitHub issues every morning:
> label them, find duplicates, and draft a reply for the ones that need info.

The skill then:

1. Looks at your repo (existing agents, skills, MCP config, harness folders).
2. Interviews you until every design decision is made, then shows you a summary table to approve.
3. Writes `.agent-architect/<system>/blueprint.yaml` and validates it.
4. Renders agent, skill and orchestrator files for your harnesses.
5. Validates the output, then walks you through `SETUP.md`: MCP servers to approve,
   environment variables to export, and the command that runs the system.

Run the result with, for example, `/fleet Use the /triage-issues skill` in Copilot CLI or
`/triage-issues` in Claude Code.

Already have agents? Ask it to **audit** them. The validator works on any project:

```bash
python3 skills/agent-architect/scripts/validate.py --out /path/to/project
```

## What gets generated

| | Skills (incl. orchestrator) | Agents | MCP snippet for |
|---|---|---|---|
| Claude Code | `.agents/skills/` + links in `.claude/skills/` | `.claude/agents/*.md` | `.mcp.json` |
| Copilot CLI | `.agents/skills/` | `.github/agents/*.agent.md` | `.mcp.json` |
| Codex | `.agents/skills/` | `.codex/agents/*.toml` | `.codex/config.toml` |
| Gemini CLI | `.agents/skills/` | `.gemini/agents/*.md` | `.gemini/settings.json` |
| Cursor | `.agents/skills/` | `.cursor/agents/*.md` | `.cursor/mcp.json` |
| OpenCode | `.agents/skills/` | `.opencode/agents/*.md` | `opencode.json` |

Plus `.agent-architect/<system>/` with the blueprint, a decision log, `SETUP.md`, and a
manifest. The manifest lets re-renders update and clean up only the files the renderer
itself created. Capability and model mapping per harness:
[references/harnesses.md](skills/agent-architect/references/harnesses.md).

## Examples

Both examples are rendered for all six harnesses so you can see the exact output:

- [`examples/pr-review`](examples/pr-review/): a panel of security, test and docs reviewers
  run in parallel, then a synthesizer merges their findings, then a checkpoint, then a
  publisher posts the review via the GitHub MCP server.
- [`examples/competitor-research`](examples/competitor-research/): one researcher per
  company runs in parallel, each writing its own file, then a brief-writer combines the
  results. No code involved.

## The scripts

All in `skills/agent-architect/scripts/`, Python standard library plus PyYAML:

| Script | Does |
|---|---|
| `validate.py --blueprint B` | Checks a design: names, references, least privilege, file-ownership overlaps between parallel agents, literal secrets, size limits. Prints the summary table. |
| `render.py B --out DIR --harness all` | Writes the files. `--dry-run` previews. Refuses to overwrite files it did not create (`--force` to override). |
| `validate.py --out DIR` | Checks agent and skill files in any project: frontmatter, sizes, broken or nested references, empty agents, duplicate skills. |
| `mcp_search.py KEYWORD --yaml` | Searches the official MCP registry and prints blueprint-ready entries. |

## Status and limits

v0.1. Harness formats were checked against each vendor's docs in November 2026. The
test suite covers rendering, parsing and validation; the generated systems have **not yet
been run end to end in all six harnesses**. Reports from real runs are the most useful
contribution. Known gaps:

- Codex agent files cannot set the sandbox, so read-only Codex agents are read-only only by
  instruction.
- Gemini CLI sub-agents cannot spawn other agents, so nesting designs are not portable.
- Copilot, Gemini, Cursor and OpenCode model tiers are left to the harness default unless
  you pin a model id per harness.
- OpenCode output uses the v1 `permission` fields, which v2 still reads.

## Credits

This project builds on ideas from other people's work, written up in its own words. See
[CREDITS.md](CREDITS.md).

## License

MIT. See [LICENSE](LICENSE).
