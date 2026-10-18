## Structural acceptance criteria (checked before the PR)
- Every runtime file is at most 200 lines of logic, and every runtime function at most 15, **measured by the
  framework's own tool** (`test_framework_meets_its_own_limits`).
- 22 skills exist (the Tasks 7–11 lists add up to 22; an earlier "21" here was a miscount), each passing `test_skills.py`. No `SKILL.md` names a language or a project.
- `docs/coverage.md` ends with `**Gaps: 0**`, and the three `--source` cross-checks report no gaps.
- `apm debt check` fails on each gaming attempt listed in Review Focus 3.
- No Plan 1 test was weakened. Any Plan 1 test that changed was changed on purpose for a new rule (for example
  the subcommand list), and the PR says so.

## After the criteria
- Not a criterion.
