# Issue 27: generic example names, and the guard freeze recorded

Issue: #27. Branch: `issue-27-generic-examples`, cut from origin/main ea0e5e7. Lane: default. Review: one whole-branch
review at the end. No task touches a `guard*` module, so there are no per-task reviews.

## Goal
APM is a general framework. A few files on main still use the user's other project (VirtualAirline, X-Plane, XP12)
as example values. Swap them for generic ones. Also record the user's decision of 2026-10-24 to freeze the guard,
so a later reader knows why #13, #15 and #21 were closed.

## Global constraints
- Scope by the user's decision: the tests, the ADRs and the one code comment. `docs/plans/`, `docs/specs/`,
  `docs/platform-notes.md`, `docs/coverage.md` and `standard/coverage.json` stay as they are, as history.
  `tests/test_skills.py` keeps its word list, which checks that skills stay free of these names.
- No test may lose what it checks. A renamed path keeps every property the test relies on (a space in the name,
  the slug's shape).
- Ruling: rewording an example name in an accepted ADR does not change its decision, so it is not the kind of
  edit `apm:adr` forbids. The decision text, the counts and the status lines stay. *Cost if wrong: two ADRs
  differ in wording from what was accepted.*

## Task 1: generic names in the tests, ADRs 0003 and 0006, and the comment
Files:
- `tests/test_guard_bypasses.py:9`: `SPACED = "C:/Users/me/source/repos/Sample App"` (keep the space)
- `tests/test_guard_memory_folder.py:17-18`: `C:\Users\me\source\repos\Sample-App` and its slug
  `C--Users-me-source-repos-Sample-App`
- `tests/test_metrics_cpp.py:141,145`: `test_the_database_header_has_seven_public_methods`,
  `test_the_map_screen_header_has_eight_public_methods`
- `docs/adr/0003-newly-measured-classes-are-not-new-debt.md:10`: "the unchanged XP12 tree" becomes "an unchanged
  C++ project's tree"
- `docs/adr/0006-the-main-session-writes-its-memory-folder.md:10`: "the VirtualAirline XP12 project" becomes
  "another project"
- `scripts/apm/metrics_cpp_heads.py:107`: "as XP12's checker reads them" becomes "as a typical C++ access
  checker reads them"

Test: `python -B -m pytest -q tests/test_guard_bypasses.py tests/test_guard_memory_folder.py tests/test_metrics_cpp.py tests/test_docs.py tests/test_skills.py`
gives the same pass count as before the change. Then
`git grep -n -i -E "xp12|x-plane|virtualairline" -- tests/test_guard_bypasses.py tests/test_guard_memory_folder.py tests/test_metrics_cpp.py docs/adr scripts`
prints nothing.

## Task 2: ADR 0008, the guard is frozen
Add `docs/adr/0008-the-guard-is-frozen-at-issue-20.md`, and its row in `docs/adr/README.md`.
- **Decision:** after #20 (PR #28), the guard gets no new command-reading rules. Dangerous actions stay blocked
  until the user approves them in chat: destructive commands, protected paths, `.git`, APM state, and writes
  outside the project. A false alarm on harmless work that has a workaround (the Read tool, `git show`) is
  accepted rather than fixed. A guard change is made only when a false alarm blocks real work with no
  workaround, or when a dangerous action gets through.
- **Context:** issues #11, #14, #19 and #20 each refined how the guard reads shell text, and each fix opened the
  next false alarm (#13, #15, #21). The user: "if anything is dangerous the agent needs to ask the users
  permission then it can do it".
- **Consequences:** a worker sometimes falls back to the Read tool. #13, #15 and #21 are closed as not planned.
  The known limits named in ADR 0007 and the guard docstrings stay limits.
- **Alternatives:** keep fixing each false alarm (rejected: unbounded parsing work for no safety gain); cut the
  guard down to the hard rules only (rejected for now: a bigger change, not asked for).
- Status: `Accepted, 2026-10-24. Builds on ADR-0002 and ADR-0007.` Neither of those records changes.

Test: `python -B -m pytest -q tests/test_docs.py`.

## Task 3: the merge gate
`<CLI> gate 27`.

## Structural acceptance criteria
- `git grep -n -i -E "xp12|x-plane|virtualairline"` over `tests/test_guard_bypasses.py`,
  `tests/test_guard_memory_folder.py`, `tests/test_metrics_cpp.py`, `docs/adr/` and `scripts/` prints nothing.
- `docs/adr/0008-the-guard-is-frozen-at-issue-20.md` exists and is listed in `docs/adr/README.md`.
- No file outside the Task 1 and Task 2 lists changes; no `guard*` module changes.
- Every file stays within 200 lines of logic and every function within 15; `debt check` is clean.

## Pre-flight scan
| Check | Finding |
|---|---|
| Task 1 vs Task 2: shared files | None: Task 1 edits three tests, ADRs 0003 and 0006, and one comment; Task 2 adds ADR 0008 and a README row. |
| Task 1 self-consistency | The renames keep the space in `SPACED` and the slug's shape; the grep criterion matches the file list. |
| Task 2 self-consistency | ADR 0008 builds on 0002 and 0007 and edits neither. |
| Rubric conflicts | None. |

*Ruling before Task 1: the two tasks are small and of one kind (doc and example edits), so one worker builds both, as two commits. Cost if wrong: none.*

*Ruling on the final review (2026-10-24): S1 is right; Task 2's own wording was wrong. APM state, a file-tool write outside the project, and a worker's denial have no approval (ADR-0006, ADR-0007). ADR 0008's first Decision bullet becomes "What stays blocked": the same list, then "where ADR-0006 and ADR-0007 allow an approval, the user gives it in chat; the rest stay unapprovable". G1 and G2 are folded into the same round: drop "They are not defects to be filed.", qualify "a dangerous action gets through" with ADR-0002's test (a command a cooperative worker would produce while following its brief), and in the Context say the issues "each refined the guard's rules" rather than claiming all four were about reading shell text. Cost if wrong: none; wording only.*
