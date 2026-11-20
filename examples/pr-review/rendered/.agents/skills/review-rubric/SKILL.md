---
name: review-rubric
description: Severity scale and wording rules shared by all PR reviewers. Use when rating or writing a code review finding.
metadata:
  generated-by: agent-architect
---

# Review rubric

Rate every finding with exactly one severity:

| Severity | Meaning | Example |
|---|---|---|
| blocker | Will cause an incident, data loss or a security hole if merged. | SQL built from request input. |
| major | Wrong behaviour or a real gap a user will hit. | New error path with no test. |
| minor | Correct but fragile, unclear or inconsistent. | Docstring out of date. |
| nit | Taste. Only report if asked. | Naming preference. |

Wording rules:
- Point to `file:line` in the diff. No line, no finding.
- Say why it matters in one sentence, in terms of impact on users or maintainers.
- Suggest a concrete fix, not "consider improving".

For borderline security ratings, read the examples reference.

## References

- [references/security-examples.md](references/security-examples.md) — read when unsure whether a security finding is a blocker or major
