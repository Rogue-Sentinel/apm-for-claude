# APM for Claude — Issue 36: Release apm 0.3.4 — Implementation Plan

> **For agentic workers:** the manager builds this plan. One implementer builds Task 1 in its own worktree, and the
> manager verifies it with its targeted tests. The whole branch is reviewed once at the end. The full suite runs once,
> through the merge gate.

**Goal:** Publish #34 as apm 0.3.4, so installed projects pick it up.

**Architecture:** A version bump in the two places the plugin declares its version, plus the tutorial's profile example. The manager records 0.3.4 in this repo's own `.apm/profile.json`, as it did for 0.3.1 (#17), 0.3.2 (#25) and 0.3.3 (#30). The release changes no behavior.

**Spec:** GitHub issue #36. The release follows the shape of 0.3.3 (`docs/plans/2026-10-24-issue-30-release-0.3.3.md`).

## Global Constraints
- The version string is exactly `0.3.4`.
- No behavior changes, and no test is edited. Fixtures that build a `Profile(framework_version="0.3.0")` are test data and stay as they are.
- Merge style: `merge` (profile).

## Review Focus
1. **No stale version is left where users read it.** The plugin manifest, `apm.VERSION`, this repo's profile and the tutorial example all say 0.3.4.

## File Structure
```
.claude-plugin/plugin.json   (modify) "version": "0.3.4"
scripts/apm/__init__.py      (modify) VERSION = "0.3.4"
docs/tutorial.md             (modify) the section 9 profile example: "framework_version": "0.3.4"
.apm/profile.json            (modify, by the manager) "framework_version": "0.3.4"
```

### Task 1: Bump the version to 0.3.4
- [ ] **Step 1:** Run `python -B -m pytest -q tests/test_setup.py tests/test_docs.py tests/test_cli.py` as the baseline. Expected: PASS.
- [ ] **Step 2:** Change the three strings above from `0.3.3` to `0.3.4`. Change nothing else.
- [ ] **Step 3:** Run the Step 1 command again. Expected: PASS.
- [ ] **Step 4:** Commit `"Release #34 as apm 0.3.4"`.

The manager then commits `.apm/profile.json` at `0.3.4` on the branch, with the message `"Record framework 0.3.4 in this repo's profile"`.

### Task 2: Run the merge gate
- [ ] **Step 1:** Run `<CLI> gate 36`. Expected: PASS.

## Structural acceptance criteria (checked before the PR)
- `.claude-plugin/plugin.json`, `scripts/apm/__init__.py`, `docs/tutorial.md` (the section 9 example) and `.apm/profile.json` say `0.3.4`. No other tracked file outside `docs/plans/`, `docs/specs/` and `docs/platform-notes.md` names `0.3.3` as the current version.
- No test is edited.
- `<CLI> debt check` passes, and `<CLI> gate 36` passes.

## Allowlisted actions
None.

## Approval (2026-10-24)
*The user asked in chat to "file and run the release of apm 0.3.4 with #34". That request names this plan's whole scope: a version bump, with no decision left open.*
