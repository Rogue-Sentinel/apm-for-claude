# APM for Claude — Issue 25: Release apm 0.3.2 — Implementation Plan

> **For agentic workers:** the manager builds this plan. Task 1 is built by one implementer in its own worktree and verified by the manager with its targeted tests. The whole branch is reviewed once at the end, and the full suite runs exactly once, through the merge gate, right before the PR. No task is safety-critical. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the #14 and #19 fixes as apm 0.3.2 so that installed projects pick them up.

**Architecture:** A version bump in the two places the plugin declares its version, plus the tutorial's profile example. The manager records 0.3.2 in this repo's own `.apm/profile.json`, as it did for 0.3.1 (#17). No behavior changes.

**Tech Stack:** Python 3, pytest. Test command: `python -m pytest -q <files>`.

**Spec:** GitHub issue #25. The release follows the shape of 0.3.1 (`docs/plans/2026-10-18-issue-17-release-0.3.1.md`).

## Global Constraints
- The version string is exactly `0.3.2`.
- No behavior change, and no test edited. Fixtures that build a `Profile(framework_version="0.3.0")` are test data and stay as they are.
- Merge style: `merge` (profile).

## Review Focus
1. **No stale version left where users read it.** The plugin manifest, `apm.VERSION`, this repo's profile and the tutorial example all say 0.3.2. Checked in Task 1 by `tests/test_setup.py` and by the manager's grep.

---

## File Structure

```
.claude-plugin/plugin.json   (modify) "version": "0.3.2"
scripts/apm/__init__.py      (modify) VERSION = "0.3.2"
docs/tutorial.md             (modify) the section 9 profile example: "framework_version": "0.3.2"
.apm/profile.json            (modify, by the manager) "framework_version": "0.3.2"
```

### Task 1: Bump the version to 0.3.2

**Files:**
- Modify: `.claude-plugin/plugin.json`, `scripts/apm/__init__.py`, `docs/tutorial.md`

**Interfaces:**
- Produces: `apm.VERSION == "0.3.2"`.

- [ ] **Step 1:** Run `python -m pytest -q tests/test_setup.py tests/test_docs.py tests/test_cli.py` as the baseline. Expected: PASS.
- [ ] **Step 2:** Change the three strings above from `0.3.1` to `0.3.2`. Change nothing else.
- [ ] **Step 3:** Run the Step 1 command again. Expected: PASS.
- [ ] **Step 4:** Commit `"Release the #14 and #19 fixes as apm 0.3.2"`.

The manager then commits `.apm/profile.json` at `0.3.2` on the branch, with the message `"Record framework 0.3.2 in this repo's profile"`.

### Task 2: Run the merge gate

- [ ] **Step 1:** Run `<CLI> gate 25`. Expected: PASS.

---

## Structural acceptance criteria (checked before the PR)
- `.claude-plugin/plugin.json`, `scripts/apm/__init__.py`, `docs/tutorial.md` (the section 9 example) and `.apm/profile.json` say `0.3.2`. No other tracked file outside `docs/plans/`, `docs/specs/`, `docs/platform-notes.md` and the test fixtures still names `0.3.1`.
- No test edited.
- `<CLI> debt check` passes. `<CLI> gate 25` passes. Merge style: `merge`.

## Allowlisted actions
None.

## Approval (2026-10-20)

*The user asked in chat: "Continue #19: verify and review Task 3, then the final review, gate, PR and merge, then release 0.3.2 with #14 and #19." The request names this plan's whole scope: a version bump, with no decisions left open. As with 0.3.1 (#17), the manager takes it as the approval of this one-task plan and says so in its reply.*
