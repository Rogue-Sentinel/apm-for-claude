---
name: initializing
description: "Use when the user asks to set a project up under the framework, to adopt it, or to take over an existing codebase; when a project has no profile yet; or when the manager is tempted to replace the project's own standards or skills before the user has seen what is there."
---

# Initializing a project

Audit first, show the user what is there, and change nothing until they approve. A project arrives
with branches in flight, plans half-built, standards of its own and debt nobody has counted.
Initialization takes all of it in without losing any of it.

The manager runs this workflow. Workers audit and report; they never write the files that
initialization applies.

## When this applies

- The user asks to set up, adopt or initialize the framework in a project.
- A session starts in a project with no `.apm/profile.json`.
- The user asks what is in a codebase before anything is changed.

It does not apply to a project that is already initialized. A change to its profile is an ordinary
tracked edit.

## The core rule

**Nothing is overwritten until the user approves the audit, and nothing is approved while the
capability coverage table shows a gap.**

Breaking the letter of this rule is breaking its spirit: a "preview" that already replaced a file,
or an approval asked for while a row of the table is empty, is the violation. The audit is read-only
and so is everything the auditors do. The first change to the project is the one the approved audit
names.

## Existing or fresh

Run `<CLI> audit` from the project root. It reads only; it works in any git repository and exits 2
when there is no repository. Read its `mode`:

- **Existing:** some tracked file has a known language. Run the full workflow below.
- **Fresh:** no code yet. Skip to "A fresh project".

The audit measures the tree at its **base**, which is `origin/main`, else `main`, else the `master`
forms, after a fetch. Anything it could not read (no `origin`, no `gh`, not signed in, no commits)
is a line in its notes. Pass each note on to the user; do not guess around it.

Create the init issue first with `<CLI> issue N --kind feature --title "Initialize the framework"`,
set it to `designing`, and work on its branch. If GitHub is reachable, file it with
`<CLI> github file` so the number is real (see `apm:running-an-issue`).

## Dispatching the auditors

Dispatch `apm:auditor` workers with `apm:clean-code-audit`: at most three at once, each on a
**disjoint part of the tree** (`apm:parallel-dispatch`). Each reads from the audit's base, not the
local checkout, so uncommitted edits and a stale branch do not change what is measured. Use the
brief in [references/auditor-brief.md](references/auditor-brief.md).

Each auditor reports its part of the draft profile, a rule-by-rule inventory of the standards it
found, and the in-flight work it saw. The manager merges the parts. Run the numbers yourself
(`<CLI> metrics --json --ref <base>`): an auditor's numbers are a claim.

## The audit report

Write the report for the user in plain language, from the template in
[references/audit-report-template.md](references/audit-report-template.md): the mode, the
measurements at the base, the in-flight work with a decision for each item, the debt issues, the
capability coverage table, and the notes.

Save the files init reads under `.apm/audit/`: `audit.json` (the output of `<CLI> audit --json`),
`profile.json` (the draft profile), `coverage.json` and `decisions.json`. Workers cannot write
there; the manager writes them, after the user decides.

## The capability coverage table

The project's own standards (its instruction files, style guides, lint rules, skills) are
**inventoried rule by rule** into `.apm/audit/coverage.json`, in the shape of the framework's
`standard/coverage.json`. Each rule is one row: where it came from, and where the framework covers
it, keeps it as domain knowledge, or declares it an override.

- A rule with no row is a gap, and `<CLI> coverage` reports it. Approval waits until `Gaps: 0`.
- A rule the framework does not cover is not dropped. It becomes a domain skill the project keeps
  (`apm:writing-skills`, "Domain skills belong to the project") or a declared override.
- A fresh project has nothing to inventory, so `coverage.json` may be absent.

## In-flight work

The audit lists every unmerged branch, every worktree, every plan and spec on disk, and every open
issue. Ask the user to decide each item, one of three:

- **Finish first:** the work lands on the base before initialization. Init refuses while that branch
  is not merged. Offer this for work that is nearly done.
- **Adopt:** the item comes under the framework. An issue becomes a queued, imported issue. A plan or
  spec becomes a decision note, and **an imported plan is not approved**: it needs the user's
  approval before anything is built from it.
- **Leave:** the item is recorded and left alone.

Stale worktrees are reported, never removed (`apm:worktrees`). A worktree whose folder is gone, or
one with uncommitted changes, goes in the report with that detail, and the user decides what to do
with it by hand. Record the decisions in `.apm/audit/decisions.json`, one value per item.

## Overwrite versus keep

The framework replaces **methodology**: how to test, review, refactor, plan, debug and finish a
branch. It keeps **domain knowledge**: facts true only of this project, such as a screen's layout,
its environment paths, its decision records and its domain skills.

- A methodology file is replaced once the coverage table shows its every rule covered, and the user
  has approved the overwrite.
- A file that mixes both is split: the methodology part is covered by a framework skill, and the
  domain part stays.
- A methodology choice the project insists on (a merge style, a test command, a review cadence,
  safety-critical paths, lanes) becomes a declared override under `workflow` in the profile. It is
  never a quiet edit to a framework skill.

## Approval, then apply

1. **Show the report** and the coverage table. Ask for approval of the whole audit: the draft profile,
   the decision for every in-flight item, and the methodology files that will be replaced.
2. **After the user approves in chat,** write the four files under `.apm/audit/`.
3. **Run `<CLI> init --issue N`.** It refuses, with one line per reason, when a file is missing, the
   coverage has a gap, an item has no decision, a "finish first" branch is not merged, or the draft
   profile does not load. Fix the cause and run it again. It never edits methodology files.
4. **Replace the methodology files** as tracked edits on the init branch, following the approved
   audit. Any deletion is named in the plan and recorded with `<CLI> allow`, so it is on the
   allowlist; an unplanned deletion is reverted.
5. **Verify, then finish** with `apm:merge-gate` and `apm:finishing-a-branch`: the pull request
   carries the audit report. Running `<CLI> init` twice adds nothing the second time.

## Debt issues

Existing debt issues (a `[Debt]` title or a `debt` label) are **adopted, not duplicated**: init
merges their numbers into the ledger.

The audit's measurements may show debt nobody has filed. Offer the user a **short ranked list,
grouped by area**, with the worst first, and file only what they approve, one at a time:
`<CLI> github file --kind debt --title T --body-file PATH`. The baseline records today's numbers as
the floor; it does not require paying the list down.

## A fresh project

There is nothing to audit or overwrite. Write the design with `apm:design-first`, then a scaffold
plan with `apm:writing-plans`: the layers, the test setup, the build and the first feature. Run
`<CLI> setup`, write the profile from the user's answers, and build under `apm:executing-plans`.
The first debt baseline is recorded once the scaffold exists.

## Quick reference

| Step | Command or output | Who |
|------|-------------------|-----|
| Read the project | `<CLI> audit [--json]` | manager; workers may run it |
| Measure the base | `<CLI> metrics --json --ref <base>` | manager, auditors |
| Check coverage | `<CLI> coverage` (must print `Gaps: 0`) | manager |
| Apply the approved audit | `<CLI> init --issue N` | manager only |
| File a debt issue | `<CLI> github file --kind debt` | manager only, user approved |

## Red flags

- A methodology file was replaced before the user approved the audit.
- The coverage table has a gap and approval is being asked for.
- An imported plan is being built without the user's approval.
- A worktree or branch is being removed because it "looks stale".
- A debt issue is filed that an existing one already covers.

## References

- [references/audit-report-template.md](references/audit-report-template.md): the audit report the
  user reads, section by section.
- [references/auditor-brief.md](references/auditor-brief.md): the brief for an auditor on one part of
  the tree.

## Common mistakes

- **Dispatching more than three auditors**, or two on overlapping parts of the tree.
- **Auditing the local checkout** instead of the base, so the numbers describe uncommitted work.
- **Asking for approval with a gap in the table**, or treating an uninventoried rule as covered.
- **Approving an imported plan by adopting it.** Adoption records it; the user approves it.
- **Removing a stale worktree.** The audit reports; the user decides, by hand.
- **Overriding methodology by editing a framework skill**, not by declaring it under `workflow`.
- **Filing every debt issue at once.** File the short list the user approved.
- **Running init before the "finish first" branches have merged.**
