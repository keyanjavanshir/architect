# Blueprint schema

The blueprint is the single source of truth. Keep it in
`.agent-architect/<system>/blueprint.yaml` and commit it. Everything in `.claude/`,
`.github/agents/`, `.codex/`, `.gemini/`, `.cursor/`, `.opencode/` and `.agents/skills/`
that the renderer writes is derived from it.

Names everywhere are kebab-case: `^[a-z0-9]+(-[a-z0-9]+)*$`, at most 64 characters, unique
across agents, skills and the orchestrator. The same name is used in every harness, so the
orchestrator can refer to agents by name.

## Top level

```yaml
version: 1
system:
  name: pr-review              # required
  description: One paragraph.  # required, used in SETUP.md
  harnesses: [claude-code, copilot-cli]   # default targets; --harness overrides
  requirements:                # optional: tools the user installs once; listed in SETUP.md
    - "ffmpeg on PATH (Windows: winget install Gyan.FFmpeg)"
orchestrator: {...}            # optional; omit for a single standalone agent or skill
agents: [...]
skills: [...]
mcp_servers: [...]
```

Harness ids: `claude-code`, `copilot-cli`, `codex`, `gemini-cli`, `cursor`, `opencode`.

## orchestrator

Rendered as a skill, so it runs in the main session (the only place that can spawn
sub-agents in every harness).

| Field | Req | Meaning |
|---|---|---|
| `name`, `description` | yes | Skill name and trigger description. |
| `argument_hint` | no | What the user passes, e.g. `"<PR number>"`. |
| `manual_only` | no | `true` = only runs when invoked by name. Default `true` if any checkpoint exists. |
| `instructions` | no | Markdown: preparation before the first wave (gather inputs, split work). |
| `waves` | yes | Ordered list. Each wave finishes before the next starts. |
| `checkpoints` | no | Human approvals: `{after: <wave>, ask: "..."}` or `{before: <wave>, ask: "..."}`. |
| `on_failure` | no | `retry-once` (default), `skip-and-report`, or `stop`. |
| `output` | yes | The final deliverable and where it goes. |

A wave:

```yaml
- name: review                  # kebab-case, unique
  agents: [security-reviewer, test-reviewer]
  for_each: changed package     # optional: one instance per item; describe the unit
  max_parallel: 6               # optional cap on concurrent instances
  pass: Diff of the package and the PR description.   # what each brief must include
```

## agents

| Field | Req | Meaning |
|---|---|---|
| `name`, `description` | yes | Description says what it does **and when to delegate to it**. |
| `prompt` | yes | Role, method, constraints. Under 80 lines. No harness-specific tool names. |
| `returns` | yes | Output contract: format, sections, length. |
| `capabilities` | no | Subset of `read, search, edit, shell, web, delegate`. Default `[read, search]`. |
| `owns` | if `edit` | Paths/globs this agent may write. Parallel agents must not overlap. |
| `mcp` | no | Names from `mcp_servers`. |
| `skills` | no | Skill names the agent should load (preloaded where the harness supports it). |
| `model` | no | `inherit` (default), `fast`, `balanced`, `strong`. See harnesses.md for mapping. |
| `models` | no | Per-harness exact model id, e.g. `{opencode: anthropic/claude-sonnet-5-5}`. |
| `max_turns` | no | Turn cap where the harness supports it. |

## skills

Generated skill:

```yaml
- name: security-checklist
  description: What it covers and when to use it.
  body: |                       # SKILL.md body, under 200 lines
    ...
  references:                   # optional, one level deep, linked from body automatically
    - path: owasp-top-10.md
      when: read when a finding needs a category   # used in the auto-generated link list
      content: |
        ...
  scripts:                      # optional
    - path: check.py
      content: |
        ...
```

Reused skill (not generated; listed in SETUP.md with its install command):

```yaml
- name: grill-me
  description: Interview the user about a plan.
  install: npx skills add mattpocock/skills --skill grill-me
```

## mcp_servers

```yaml
- name: github                  # the name agents use in `mcp:`
  why: Read PR diffs and post review comments.
  transport: http               # stdio | http
  url: https://api.githubcopilot.com/mcp/
  headers: {Authorization: "Bearer ${GITHUB_TOKEN}"}
  docs: https://github.com/github/github-mcp-server
- name: playwright
  why: Open the preview deployment and screenshot changed pages.
  transport: stdio
  command: npx
  args: ["-y", "@playwright/mcp@latest"]
  env: {}
```

Every secret is written as `${VAR}`. The validator rejects values that look like literal
tokens. SETUP.md lists each `${VAR}` the user must export.
