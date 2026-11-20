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
