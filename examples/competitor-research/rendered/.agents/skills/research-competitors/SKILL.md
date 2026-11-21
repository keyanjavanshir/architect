---
name: research-competitors
description: Builds a sourced comparison of competitors by researching each one in parallel. Use when the user gives a list of companies or products to compare.
argument-hint: "<comma-separated company names> [focus, e.g. pricing]"
metadata:
  generated-by: agent-architect
  role: orchestrator
---

# /research-competitors

You coordinate the **competitor-research** system. Do preparation and synthesis yourself; delegate each unit of work to the named sub-agent. Start every agent in a wave at the same time when your harness can run sub-agents in parallel, and finish a wave before starting the next.

**Input:** <comma-separated company names> [focus, e.g. pricing]. If it is missing, ask for it before doing anything else.

## Preparation

1. Parse the company names and the optional focus. If there are more than 10, ask the
   user to narrow the list.
2. Turn each name into a short slug (lowercase, hyphens) for its file name.
3. Confirm the list and the focus with the user in one line, then start.

## Waves

### 1. Research (in parallel)

- Run one instance of each agent per **company**, at most 5 at a time. Replace `{item}` in owned paths with a short slug for the item.
- Agents: `company-researcher`
- Each brief must include: The company name, its slug, the focus, and today's date.

### 2. Compare (one agent)

- Agents: `brief-writer`
- Each brief must include: The list of profile paths under `research/companies/` and the focus.
- Include the relevant results of the previous wave in each brief; the agents cannot see them otherwise.

## Writing a brief

Sub-agents start with no memory of this conversation. Every brief contains:

1. **Goal** — one sentence and how success is judged.
2. **Inputs** — the content itself, or exact paths, URLs or IDs.
3. **Scope** — the files it owns for this run and anything off limits.
4. **Context** — decisions already made that constrain the work.
5. **Return** — the format the agent's definition asks for, in at most five lines plus file paths; details belong in files, not in this conversation.

Start a fresh agent for follow-up work instead of resuming one that has been idle for more than a few minutes; give it only the files it needs.

## Failures

If a unit fails, do not retry. Continue and list it under **Skipped** in the output with the reason.

## Output

`research/brief.md` — a comparison table plus key takeaways — with every claim linked to a source. Show the takeaways to the user.

## Agents

| Agent | Use for | May write |
|---|---|---|
| `company-researcher` | Researches one company from public sources and writes a structured, sourced profile | `research/companies/{item}.md` |
| `brief-writer` | Combines several company profiles into one comparison brief | `research/brief.md` |

## Running sub-agents

- Copilot CLI: this skill works best under `/fleet`, which runs the agents in parallel.
- Claude Code, Codex, Gemini CLI, Cursor, OpenCode: spawn each agent by its exact name.
- If your harness cannot spawn sub-agents, do each unit yourself in order, following that agent's definition.
