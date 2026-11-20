# Design rules for generated files

Context is shared and finite. Everything you generate is loaded into some agent's window,
so every line must earn its place. The validator enforces the numbers below.

## Sizes

| File | Limit | Why |
|---|---|---|
| Skill/agent `description` | ≤ 1024 chars (aim for 1–3 sentences) | Always in context for discovery. |
| Generated `SKILL.md` body | ≤ 200 lines (error at 500) | Loaded in full when triggered. |
| Agent prompt body | ≤ 80 lines (error at 30,000 chars) | Copilot CLI's hard limit is 30,000 chars. |
| Reference file | ≤ 300 lines, or add a "Contents" list at the top | Agents may read only the start. |

## Progressive disclosure

Three levels, loaded only when needed:

1. **Description** — what it does and when to use it. Always visible.
2. **Body** — the procedure: steps, decisions, pointers. Loaded when triggered.
3. **References and scripts** — details, tables, examples, code. Loaded or run on demand.

Rules:
- References are **one level deep**: `SKILL.md` links each reference directly; references do
  not send the reader on to other references.
- Each reference covers one concern, and the body says *when* to read it
  ("Read references/api-errors.md when a request returns 4xx").
- Deterministic work (parsing, validation, formatting) goes in a script, not prose. Scripts
  run without being read into context.
- Never put reference `.md` files inside an `agents/` directory: some harnesses load every
  Markdown file there as a separate agent. Agent knowledge lives in skills.

## Descriptions

- Say **what** and **when**, in the third person: "Reviews Terraform plans for drift and
  cost. Use when a PR changes files under infra/."
- Include the words a user or orchestrator would actually use.
- Never vague ("helps with code"). Never a capability list with no trigger.

## Prompts and bodies

- Write only what a capable model would not already know: conventions, constraints,
  decisions, the exact output format. Cut generic advice ("write clean code").
- Replace adjectives with checks: not "thorough", but "cover every changed file; cite
  file:line for each finding".
- State constraints as rules with the reason attached: "Do not edit files outside `owns` —
  other agents are writing in parallel."
- Use the neutral tool vocabulary (read, search, edit, run, fetch). The renderer maps
  capabilities to each harness; tool names in prose go stale across harnesses.
- End every agent prompt with its return contract (the renderer appends `returns`).

## Least privilege

- Default capabilities are `read, search`. Add `edit`, `shell`, `web`, `delegate` only when
  a decision in the interview requires it, and record why in the decision log.
- Only the orchestrator delegates by default. Gemini CLI sub-agents cannot spawn others at
  all, so designs that need nesting are not portable.
- MCP servers are attached per agent, not globally, wherever the harness allows it.

## Naming

- kebab-case, role-first: `security-reviewer`, `release-notes-writer`, `review-pr`.
- The orchestrator is named for the action the user invokes (`review-pr`), agents for the
  role they play.
