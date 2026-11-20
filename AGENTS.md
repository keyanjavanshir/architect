# Working on agent-architect

Instructions for coding agents (and humans) changing this repository.

## Layout

- `skills/agent-architect/` — the skill users install. `SKILL.md` is the entry point;
  `references/` hold detail loaded on demand; `scripts/` are run, not read.
- `examples/<name>/blueprint.yaml` — example designs; `rendered/` is their committed output.
- `tests/` — `python3 -m unittest discover -s tests`.

## Rules

- Keep `SKILL.md` under 200 lines and each reference under 300. Link every reference
  directly from `SKILL.md`; references never link to other references.
- Scripts use only the standard library plus PyYAML, and Python 3.11+.
- When you change `render.py`, re-render the examples and commit the result; a test fails
  if `examples/*/rendered` is stale:

  ```bash
  for x in examples/*/; do
    python3 skills/agent-architect/scripts/render.py "$x/blueprint.yaml" --out "$x/rendered" --harness all
  done
  ```

- When a harness changes its format, update `render.py`, `references/harnesses.md` and the
  tests together, and cite the vendor doc in the PR.
- Never add behaviour that writes MCP config, settings, or anything in the user's home
  directory without an explicit approval step.
- Run the tests and `validate.py --out . --strict` before committing.
