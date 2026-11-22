# Orchestration patterns

## Where the orchestrator runs

The orchestrator is a **skill run by the main session**, not a sub-agent. The main session
is the only place that can spawn sub-agents in every harness (Gemini CLI sub-agents cannot
spawn others; Claude Code allows nesting but caps the depth). Workers are agents.

## Patterns

| Pattern | Shape | Use when |
|---|---|---|
| Fan-out | 1 wave, 1 agent × N items | Same job on many independent items. |
| Panel | 1 wave, K different agents on the same input | Several viewpoints (security, tests, UX). |
| Pipeline | waves in sequence, each feeding the next | Stages depend on each other. |
| Fan-out + reduce | wave of workers, then one synthesizer | Many partial results → one deliverable. |
| Evaluator loop | worker, then reviewer; repeat at most twice | Output quality can be checked against criteria. |

Prefer the simplest pattern that fits. Cap evaluator loops; unbounded loops burn budget.

## Briefs: workers start with nothing

A worker cannot see the orchestrator's conversation. Each dispatch must include:

1. **Goal** — one sentence, plus the acceptance check.
2. **Inputs** — the actual content or exact paths/URLs/IDs to fetch. Not "the PR we
   discussed".
3. **Scope** — files it owns (may write) and may read; what is off limits.
4. **Context** — decisions already made that constrain it.
5. **Return** — the format from the agent's `returns`, and where to write it if it writes.

The rendered orchestrator includes this template. Wave `pass:` says what goes in Inputs.

## File ownership

Parallel agents share one filesystem with no locking: when two write the same file, the
last writer wins silently. Therefore:

- Every agent with `edit` declares `owns`. Agents in the same wave must not overlap; the
  validator rejects overlaps.
- With `for_each`, ownership is per instance: use a placeholder such as
  `reports/{item}.md` so each instance writes its own file.
- Shared outputs (a summary, a changelog) are written by one agent in a later wave.
- Claude Code can isolate an agent in a git worktree; that is an optimization, not a
  substitute for ownership, because other harnesses cannot.

## Waves and width

- A wave ends when every instance has returned or failed. The next wave gets the results.
- Keep width modest (`max_parallel` 4–8) unless the user's budget allows more; each
  instance costs a full context.
- Put human checkpoints between waves, never inside one.

## Cost: tokens go where context is re-read

Every call re-reads the agent's whole context, so cost follows context size × calls.

- **Scripts first.** Script and local-model steps are `run` waves; they cost no tokens.
- **Short hand-backs.** Agents return at most five lines plus file paths; details go in
  files. The orchestrator's conversation grows with every hand-back and is re-read every turn.
- **Compact inputs for judgement.** Give a judging agent a ranked digest (a shortlist with
  measurements), not every raw log.
- **Fresh, not resumed.** An agent idle for more than a few minutes has lost its cache;
  resuming it re-pays its whole context. Start a fresh one with only what it needs.
- **Images add up.** Each image an agent views stays in its context. Combine several into
  one montage, and size batches so a context stays well under 100K tokens.
- **Long fan-outs in the main session are costly**: each finished instance wakes the
  orchestrator. For many units, prefer one script step that loops, or run the main
  session on a cheaper model.

## Failure policy

- `retry-once` (default): re-dispatch a failed unit once with the error in the brief.
- `skip-and-report`: carry on and list skipped units in the final output.
- `stop`: abort the run and report what finished.
- Always report partial results; never silently drop a unit.

## Harness launch notes

- **Copilot CLI:** run the orchestrator skill under `/fleet` to get parallel sub-agents;
  fleet picks custom agents from `.github/agents/` by their descriptions, so make them
  specific.
- **Claude Code:** invoke the skill by name (`/review-pr 123`); it dispatches named
  sub-agents. For one large mechanical change, recommend built-in `/batch` instead.
- **Codex, Gemini CLI, Cursor, OpenCode:** invoke the skill (`$name` in Codex, `/name`
  elsewhere, or ask by name); the skill tells the main agent which sub-agents to spawn.
