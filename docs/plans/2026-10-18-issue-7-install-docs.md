# APM for Claude — Issue 7: Install docs and the marketplace description — Implementation Plan

> **For agentic workers:** the manager builds this plan task by task. Each task is built test-first by one
> implementer in its own worktree and verified by the manager with the task's targeted tests. The whole
> branch is reviewed once at the end, and the full suite runs exactly once, through the merge gate, right
> before the PR. No task is safety-critical. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Someone who installed APM from a local folder learns, in the README, to remove the old
`rogue-sentinel` marketplace before adding the GitHub one, and `claude plugin validate .` passes with no
warnings because the marketplace manifest carries a description.

**Architecture:** A docs and manifest change only. One conditional note goes in the README's `## Install`
section, before the install block. The marketplace manifest gains a top-level `description`. Two new tests,
one in each existing test file, pin both.

**Tech Stack:** Markdown, JSON, pytest. Claude Code 2.1.267 for the validator.

**Spec:** GitHub issue #7.

## Platform facts this plan relies on
- *Checked 2026-10-18 against Claude Code 2.1.267.* The marketplace schema in the installed binary declares
  **both** a top-level `description` ("Human-readable description of this marketplace") and
  `metadata.description` ("Marketplace description"). The validator's warning fires only when both are
  missing (`if(!p.description&&!p.metadata?.description)`), and reports the path `description`. Confirmed
  two ways: by reading the schema and the check out of `claude.exe`, and by running `claude plugin validate .`
  on scratch copies of `.claude-plugin/` with the field at the top level, under `metadata`, and in both
  places. All three printed `✔ Validation passed` with no warning; today's manifest prints one warning.
- **Pinned: the top-level `description`.** It is the path the warning names and the same shape as
  `plugin.json`'s `description`. `metadata` is not added.
- The GitHub marketplace and a local `directory` marketplace both declare the name `rogue-sentinel`, so
  adding the GitHub one while the local one is registered fails with only "Failed to add marketplace."
  Uninstalling the plugin leaves the marketplace entry behind (from the issue).

## Global Constraints
- Everything from Plans 1 to 3 still holds: test-first, no skipped tests, no existing test weakened,
  American spelling, plain voice in user-facing docs.
- `README.md` keeps passing every test in `tests/test_docs.py`. In particular no code line or code span
  starts with `apm ` or `python `, the prose never tells the user to run `` `apm `` anything, and every
  backticked CLI word after `apm ` is a real subcommand. The new commands start with `/plugin` and `claude`,
  which none of these checks match.
- The marketplace `description` is exactly the plugin's existing text:
  `Agentic project management for Claude Code: issues, workers, and guarded tool use.`
- The manifest's `name` stays `rogue-sentinel` and `owner.name` stays `Rogue-Sentinel`
  (`test_marketplace_lists_apm_from_repo_root`). Renaming the marketplace is not this issue.
- The version stays `0.3.0`. This change ships nothing a user's installed plugin runs.

## Review Focus
Checked; one line.
1. **The note read by a brand-new user.** A first-time installer must be able to skip it without doubt: the
   note opens with its condition ("If you installed APM from a local folder before") and says a first
   install skips it. The ordering test in Task 1 pins that the remove line comes before the add line; the
   wording is the reviewer's to judge.

---

## File Structure

```
README.md                          (modify) ## Install gains the remove-the-old-marketplace note
.claude-plugin/marketplace.json    (modify) gains a top-level "description"
tests/test_docs.py                 (modify) one new test on the README install section
tests/test_manifest.py             (modify) one new test on the marketplace description
```

The README note and the manifest field are one task. Each is a few lines, both answer the same install
experience, and a reviewer who disliked the wording would send back a wording fix, not reject the manifest
line; splitting them would double the verification and records for no separate decision.

---

### Task 1: The install note and the marketplace description

**Files:**
- Modify: `README.md` (the `## Install` section only)
- Modify: `.claude-plugin/marketplace.json` (add `description`)
- Test: `tests/test_docs.py`, `tests/test_manifest.py`

**Interfaces:**
- Consumes: `section(body, heading)` from `tests/skill_helpers.py` (already imported in `test_docs.py`);
  `load(relative)` in `test_manifest.py`.
- Produces: nothing later tasks use.

- [ ] **Step 1: Write the failing tests**
  - In `tests/test_manifest.py`, `test_marketplace_describes_itself_with_the_plugin_description`:
    `load(".claude-plugin/marketplace.json")["description"]` equals
    `load(".claude-plugin/plugin.json")["description"]`, and is non-empty after `strip()`.
  - In `tests/test_docs.py`, `test_the_readme_install_says_to_remove_an_old_local_marketplace_first`: in
    `section(_text(README), "## Install")`, both `/plugin marketplace remove rogue-sentinel` and
    `claude plugin marketplace remove rogue-sentinel` appear, and the index of
    `/plugin marketplace remove rogue-sentinel` is lower than the index of `/plugin marketplace add`.
- [ ] **Step 2: Run** `python -m pytest tests/test_manifest.py tests/test_docs.py -q`. Expected: the two new
  tests FAIL (`KeyError: 'description'`; the remove line is not in the section), every other test passes.
- [ ] **Step 3: Implement**
  - `.claude-plugin/marketplace.json`: add `"description"` at the top level, after `owner` and before
    `plugins`, with the exact text from Global Constraints. Keep two-space indentation and a trailing newline.
  - `README.md`, `## Install`: split the opening line so the note sits between the marketplace sentence and
    the install block. Wording close to this, in the README's plain voice (the reviewer judges the wording):

    > The plugin lives in the `rogue-sentinel` marketplace.
    >
    > If you installed APM from a local folder before, remove that marketplace first. Uninstalling the plugin
    > leaves it behind, and because it has the same name, adding this one fails with only "Failed to add
    > marketplace." Type `/plugin marketplace remove rogue-sentinel` in Claude Code, or
    > `claude plugin marketplace remove rogue-sentinel` in a terminal. A first install skips this step.
    >
    > Then, in Claude Code:

    The install block, `/apm:setup` and the rest of the section are unchanged.
- [ ] **Step 4: Run** `python -m pytest tests/test_manifest.py tests/test_docs.py -q`. Expected: PASS.
  Then run `claude plugin validate .` in the worktree. Expected: `✔ Validation passed`, with no
  `Found 1 warning` line and no `description:` warning.
- [ ] **Step 5: Commit** `"Tell local-folder installs to remove the old marketplace, and describe the marketplace"`.

### Task 2: One review, one gate, the PR

**Files:** none changed, unless the review finds something.

- [ ] **Step 1: One whole-branch review** (`apm:reviewer`, `apm:code-review`) against `main`, pointed at the
  Review Focus and the structural criteria. Fix the findings, then record it with `<CLI> review 7` at HEAD.
- [ ] **Step 2: Run** `<CLI> gate 7`. This is the one full-suite run. Expected: `merge gate: passed`.
- [ ] **Step 3:** Push and open the PR with the gate output and the `claude plugin validate .` output. No
  commit comes after the gate.

## Allowlisted actions
None. No task writes a protected path, deletes a file, or runs a destructive command.

## Structural acceptance criteria (checked before the PR)
- Only `README.md`, `.claude-plugin/marketplace.json`, `tests/test_docs.py`, `tests/test_manifest.py` and
  this plan change on the branch.
- `claude plugin validate .` prints `✔ Validation passed` with no warnings (output in the PR).
- The marketplace `description` is top-level and equals `plugin.json`'s `description`; there is no
  `metadata` key.
- In the README's `## Install` section, `/plugin marketplace remove rogue-sentinel` comes before
  `/plugin marketplace add`, and the note is worded as conditional on an earlier local-folder install.
- Every test in `tests/test_docs.py` and `tests/test_manifest.py` passes; no existing test was changed or
  weakened.
- `<CLI> debt check` passes against `main`.
