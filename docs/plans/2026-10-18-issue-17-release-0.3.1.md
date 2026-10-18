# APM for Claude — Issue 17: Release apm 0.3.1 — Implementation Plan

> **For agentic workers:** the manager builds this plan. Task 1 is built by one implementer in its own worktree and verified by the manager with its targeted tests. The whole branch is reviewed once at the end, and the full suite runs exactly once, through the merge gate, right before the PR. No task is safety-critical. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the #9 and #11 fixes as apm 0.3.1, so that installed projects pick them up.

**Architecture:** A version bump in the two places the plugin declares its version, plus the tutorial's profile example. The manager records 0.3.1 in this repo's own `.apm/profile.json`, as it did for 0.3.0 (c0f4265), because workers may not write `.apm/`. No behavior changes.

**Tech Stack:** Python 3, pytest. Test command: `python -m pytest -q <files>`.

**Spec:** GitHub issue #17. The release follows the shape of 0.3.0 (5046f99, c0f4265).

## Global Constraints
- The version string is exactly `0.3.1`.
- No behavior change, no test edited. Fixtures that build a `Profile(framework_version="0.3.0")` stay as they are: they are test data, not the release version.
- Merge style: `merge` (profile).

## Review Focus
1. **No stale version left where users read it.** The plugin manifest, `apm.VERSION` (the SessionStart upgrade notice compares against it), this repo's profile and the tutorial example all say 0.3.1. Checked in Task 1 by `tests/test_setup.py` and the manager's grep.

---

## File Structure

```
.claude-plugin/plugin.json   (modify) "version": "0.3.1"
scripts/apm/__init__.py      (modify) VERSION = "0.3.1"
docs/tutorial.md             (modify) the section 9 profile example: "framework_version": "0.3.1"
.apm/profile.json            (modify, by the manager) "framework_version": "0.3.1"
```

### Task 1: Bump the version to 0.3.1

**Files:**
- Modify: `.claude-plugin/plugin.json`, `scripts/apm/__init__.py`, `docs/tutorial.md`

**Interfaces:**
- Produces: `apm.VERSION == "0.3.1"`.

- [ ] **Step 1:** Run `python -m pytest -q tests/test_setup.py tests/test_docs.py tests/test_plugin.py tests/test_cli.py` as the baseline. Expected: PASS. (Skip a file that does not exist, and say so.)
- [ ] **Step 2:** Change the three strings above from `0.3.0` to `0.3.1`. Change nothing else.
- [ ] **Step 3:** Run the Step 1 command again. Expected: PASS.
- [ ] **Step 4:** Commit `"Release the #9 and #11 fixes as apm 0.3.1"`.

The manager then commits `.apm/profile.json` at `0.3.1` on the branch: `"Record framework 0.3.1 in this repo's profile"`.

### Task 2: Run the merge gate

- [ ] **Step 1:** Run `<CLI> gate 17`. Expected: PASS.

---

## Structural acceptance criteria (checked before the PR)
- `.claude-plugin/plugin.json`, `scripts/apm/__init__.py`, `docs/tutorial.md` (section 9 example) and `.apm/profile.json` say `0.3.1`; no other tracked file outside `docs/plans/`, `docs/specs/`, `docs/platform-notes.md` and test fixtures still names `0.3.0`.
- No test edited.
- `<CLI> debt check` passes. `<CLI> gate 17` passes. Merge style: `merge`.

## Allowlisted actions
None.

## Approval (2026-10-18)

*The user asked in chat: "Release a new plugin version with the #9 and #11 fixes so I can keep validating in XP12, then plan #14." The request names the whole of this plan's scope (a version bump, no decisions left open), so the manager takes it as the approval of this one-task plan and says so in its reply.*
