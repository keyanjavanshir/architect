---
name: review-pr
description: "Runs a parallel security, test and docs review of a pull request and posts one merged review. Use when the user asks to review a PR by number or URL."
argument-hint: "<PR number or URL>"
disable-model-invocation: true
metadata:
  generated-by: agent-architect
  role: orchestrator
---

# /review-pr

You coordinate the **pr-review** system. Do preparation and synthesis yourself; delegate each unit of work to the named sub-agent. Start every agent in a wave at the same time when your harness can run sub-agents in parallel, and finish a wave before starting the next.

**Input:** <PR number or URL>. If it is missing, ask for it before doing anything else.

## Preparation

1. Fetch the PR title, description, and the list of changed files using the `github`
   MCP server (or `gh pr view` / `gh pr diff` if it is not configured).
2. Save the full diff to `.review/diff.patch` so every reviewer reads the same input.
3. If the diff is over 3,000 lines, tell the user and ask which paths to focus on.

## Waves

### 1. Review (in parallel)

- Agents: `security-reviewer`, `test-reviewer`, `docs-reviewer`
- Each brief must include: The PR title and description, the path `.review/diff.patch`, and the list of changed files.

### 2. Merge (one agent)

- Agents: `review-synthesizer`
- Each brief must include: The three reviewers' findings, verbatim.
- Include the relevant results of the previous wave in each brief; the agents cannot see them otherwise.

**Checkpoint:** stop and ask the user: "Here is the merged review. Post it to the PR as a comment?" Continue only on an explicit yes.

### 3. Publish (one agent)

- Agents: `review-publisher`
- Each brief must include: The path `.review/review.md` and the PR number.
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

If a unit fails, re-dispatch it once with the error added to its brief. If it fails again, continue and list it under **Failed** in the output.

## Output

`.review/review.md` with the merged review, shown to the user, and — after approval — posted as a single PR review comment. Report the comment URL.

## Agents

| Agent | Use for | May write |
|---|---|---|
| `security-reviewer` | Finds security issues in a code diff: injection, authz gaps, secrets, unsafe deserialisation, dependency risk | nothing |
| `test-reviewer` | Checks whether a diff is adequately tested: missing tests, weakened assertions, untested branches | nothing |
| `docs-reviewer` | Checks that user-facing changes in a diff are documented: README, changelog, docstrings, migration notes | nothing |
| `review-synthesizer` | Merges findings from several reviewers into one deduplicated, prioritised review | `.review/review.md` |
| `review-publisher` | Posts an approved review file as a single comment on a GitHub pull request | nothing |

## Running sub-agents

- Copilot CLI: this skill works best under `/fleet`, which runs the agents in parallel.
- Claude Code, Codex, Gemini CLI, Cursor, OpenCode: spawn each agent by its exact name.
- If your harness cannot spawn sub-agents, do each unit yourself in order, following that agent's definition.
