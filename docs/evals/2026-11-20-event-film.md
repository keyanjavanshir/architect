# Eval: designing a system with a domain pack (2026-11-20)

First live run of agent-architect with a domain-scout pack. The owner was the user; the
pack was `creative-direction-event-film` (draft) plus the owner's private overlay. The
result was `event-kickstart`: an orchestrator, six agents and four skills for Claude Code
on Windows. Rendered and validated in a scratch project; its three scripts were run on
synthetic clips and a synthetic track. Not yet run by the owner in Claude Code.

## What the pack and overlay did

- `find_pack.py` picked the right pack (score 6 vs 3 for the general film pack) and found
  the overlay.
- The overlay answered about twelve questions up front (team, client, tools, footage size,
  camera, delivery, scope), so the interview took five questions plus two design changes.
- The pack's vocabulary, structures and music/sound guidance went straight into the
  generated `event-film-craft` skill.

## Findings and what changed

| # | Finding | Fixed in |
|---|---|---|
| 1 | `find_pack.py` missed plurals ("aftermovies", "commercials"). | Plural folding in `find_pack.py`, with a test. |
| 2 | Overlay priority (music first) conflicted with the pack's build order (intention first). | `domains.md`: name the conflict and ask. |
| 3 | The user's real need ("inspire me and get me started") cut across the pack's separate teams. | domain-scout pack: a "kickstart" team. |
| 4 | The pack's tool map missed Pixabay, the user's music source (no music API). | domain-scout pack `tools.md`. |
| 5 | The architect trimmed below the pack (one still per clip); the pack said several. The user caught it. | `domains.md`: never drop pack advice silently. |
| 6 | The user added two roles the pack lacked: a clip finder and a references analyst. | domain-scout pack `patterns.md`. |
| 7 | Windows: the workflow never said to use `--no-symlinks`. | `SKILL.md` steps 1 and 5. |
| 8 | `validate.py --strict` failed every `--no-symlinks` render: it compared paths, not content. | `validate.py` `same_tree`, with a test. |
| 9 | SETUP.md called copies "symlinks". | `render.py`, with a test. |
| 10 | No place for one-time installs (ffmpeg, librosa, a LUT); SETUP.md never mentioned them. | `system.requirements` in the blueprint, rendered as "Before you start". |

## Still open

- The owner runs `/kickstart` in Claude Code on Windows on a real event; record what the
  harness disagrees with in `references/harnesses.md`.
- The orchestrator's optional waves (`zoom`, `refine`) and the interactive picks loop are
  described in instructions only; check that Claude Code follows them.

## The owner's run in Claude Code (2026-11-21)

One real event, the full `/kickstart after`, on Windows. About $13 at API list prices (the
owner measured it from the transcripts): main session (Opus) 38%, director (Opus) 31%, 11
Haiku scouts viewing about 1,800 stills 26%. The creative output was not useful; the
contact sheet was. The owner's verdict: most of the work did not need a cloud agent.

| # | Finding | Changed |
|---|---|---|
| 11 | The smallest-system test started at "one skill"; it never asked whether a step could be a script or a local model. | `interview.md`: level 0 "no agent" and an engine-per-step table. |
| 12 | No way to run a script step without an agent. | Blueprint `run` waves, rendered as "script, no agent"; validated (not with agents, not with for_each, no literal secrets). |
| 13 | Long hand-backs swelled the orchestrator's conversation, re-read on every turn. | Rendered briefs ask for at most five lines plus file paths. |
| 14 | Resuming an idle director re-paid a 216K context after its cache expired. | Rendered briefs: start fresh agents for follow-ups. |
| 15 | The director read 11 raw logs (170K tokens). Scouts' viewed images piled up, crossing the 100K price tier. Notifications woke the main session ~30 times. | `orchestration.md`: a cost section (compact digests, montages, batch sizing, long fan-outs). |
| 16 | Scouts invented details from small stills (sparklers, a medal); zooms caught them. | Kept as a reason for measured metrics and checks; see the kickstart redesign. |
| 17 | Script bugs: contact sheet ignored nested folders and showed zoom stills as duplicate clips; skill script path wrong on the owner's setup; beat map half a beat off (123 vs 120 BPM). | To fix in the kickstart redesign. |
