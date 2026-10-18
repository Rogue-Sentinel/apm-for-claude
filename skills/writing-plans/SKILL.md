---
name: writing-plans
description: "Use when you are turning an issue or an approved design into an implementation plan, or checking a plan before it goes to the user for approval, before any code is touched."
---

# Writing plans

Write the plan for an engineer who has not seen this codebase or this design. Assume they write
idiomatic code in the project's language once they know the exact interface and the exact test, and
that they make a reasonable choice wherever the plan leaves one open. What they cannot know is what
you decided: which files, which names and signatures, which values from the design, which tests
prove each task, and which structural constraints the result must meet. Document those, as
bite-sized tasks. Don't repeat yourself. Build only what is asked. Test first. Commit often.

The planner (`apm:planner`) writes the plan and reports it to the manager. The manager checks it
and shows the user a summary for approval. Neither one builds from a plan the user has not
approved.

## When this applies

- The planner has been given an issue, and for large work an approved design, to turn into a plan.
- The manager has a plan back from the planner and is checking it before the user sees it.
- Any multi-step change, before the first line of code.

## The core rule

**A plan is the set of decisions the implementer cannot make alone, and its structural
constraints are acceptance criteria, not a preamble.** File size, layering, "move, don't add", the
allowlist and every document the plan promises are part of the work. A plan that ships its
features and quietly drops its structure has not been carried out (see `apm:refactoring`, "Extract
before you add", for the time this happened).

## Before writing

1. **Read** the issue; the design document, if there is one (it is the spec the plan argues from,
   and it travels with the plan); the project profile (commands, limits, layer map, protected
   paths, overrides, lanes); the relevant decision records (`apm:adr`); and the code the work will
   touch.
2. **Measure what you will touch.** Run `<CLI> metrics` (the `apm metrics` command) on those files.
   Every one already over a limit needs an extraction task first (below).
3. **Check the scope.** If the work covers several independent subsystems, it should have been
   split during design (`apm:design-first`). If it was not, say so in your report and suggest
   separate issues, one plan each. Each plan produces working, tested software on its own.
4. **Questions only the user can answer** go back to the manager in your report. Never guess an
   answer into the plan.
5. **Where it goes:** `docs/plans/YYYY-MM-DD-<topic>.md`, unless the profile or the user names
   another place.

The planner writes the plan file and nothing else. It never changes production code.

## The plan header

Every plan starts with this header, in this order:

```
# <Project> — <Feature> — Implementation Plan

> **For agentic workers:** the manager builds this plan task by task. Each task is built
> test-first by one implementer, verified by the manager, and reviewed before the next task
> starts. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** <one or two sentences: what this builds>

**Architecture:** <two or three sentences: the approach, and where each part lives>

**Tech Stack:** <the key technologies, and the runtime limits on them>

**Spec:** <path to the design this plan implements>

## Roadmap (this plan is N of M)          -- only when the plan is one of a series
## Source material (read-only)           -- only when the work adapts existing material
## Platform facts this plan relies on    -- only when it relies on outside behavior;
                                            each fact dated, unverified ones named with
                                            the task that checks them

## Global Constraints
<the design's and the profile's project-wide requirements, one line each, with exact values
copied verbatim: limits, dependency rules, naming and spelling rules, version numbers. Every
task's requirements implicitly include this section.>

## Review Focus
<see "Review focus" below>

---

## File Structure
```

When a decision changes during the build, the plan is amended where the decision lives, in italics,
with when and why: *Changed after the Task 3 review: ...* The plan stays the record of what was
decided.

## File structure

Before defining tasks, map every file that will be created or changed, and what each one is
responsible for, in one block of path and one-line responsibility. This is where decomposition is
locked in.

```
src/orders/pricing.ext          price an order: pure, no I/O
src/orders/pricing_store.ext    load and save price tables (the only file that touches storage)
tests/orders/test_pricing.ext
```

- Design units with clear boundaries and well-defined interfaces. Each file has one clear
  responsibility.
- Prefer smaller, focused files: you reason best about code you can hold in context at once, and
  edits to focused files are more reliable.
- Files that change together live together. Split by responsibility, not by technical layer.
- In an existing codebase, follow its patterns. Do not restructure on your own initiative; but a
  file the work must change that is already unwieldy gets a split in the plan, and one over a limit
  must (below).
- Every file the plan creates lands under the file limit, and its functions under the function
  limit.

## Tasks

**Right-size each task.** A task is the smallest unit that carries its own test cycle and is worth a
fresh reviewer's gate. Fold setup, configuration, scaffolding and documentation into the task whose
deliverable needs them. Split only where a reviewer could meaningfully reject one task while
approving its neighbor. Each task ends with an independently testable deliverable.

**Name every file.** A task's files are listed exactly, so the manager can tell which tasks are
disjoint and may run in parallel (`apm:parallel-dispatch`). Say so in the plan when they may:
"Tasks 4 to 6 touch disjoint files and may run in parallel."

Each task has this shape:

```
### Task N: <component>

**Files:**
- Create: `exact/path/to/file`
- Modify: `exact/path/to/existing` (what changes in it)
- Delete: `exact/path/to/old` (why; deletion is planned, never a side effect)
- Test: `tests/exact/path`

**Interfaces:**
- Consumes: <what this task uses from earlier tasks, with exact signatures>
- Produces: <what later tasks rely on: exact names, parameters, return types>

- [ ] **Step 1: Write the failing tests**
  - `test_rejects_an_empty_order`: an order with no lines gives the error "order has no lines".
- [ ] **Step 2: Run** `<the project's test command for that file>`. Expected: FAIL (no such function).
- [ ] **Step 3: Implement** `price(order) -> Money` in `src/orders/pricing.ext`.
- [ ] **Step 4: Run** the whole suite. Expected: all PASS.
- [ ] **Step 5: Commit** `"Price an order from its lines"`.
```

**Each step is one action with a checkable result:** write the failing test; run it and see it fail;
write the least code that passes; run the tests and see them pass; commit.

**What a step contains.** A step is done when the implementer can write exactly one reasonable thing
from it: unambiguous, not complete.

- **A test step:** the test's name and its assertions, with the design's exact values in them.
- **A code step:** the exact signature (name, parameters, return type), the file it lives in, and
  the specific values the design pins. The implementer writes the body. A body appears only for an
  algorithm the signature and tests do not determine, or for exact text the design fixes.
- **A verification step:** the command to run, and the output that means it passed.
- **A reference to another task:** that task's Interfaces block says what to use; do not repeat its
  code.
- **A manual step** (a live check against a real installation): marked manual, with each result
  recorded in a named document. It is never written as a test that waits on a person.
- **A commit step:** the message, a plain sentence about the outcome. A refactoring is its own
  commit, never folded into a behavior commit.

A plan longer than the code it describes has written the code instead. Lines that decide nothing
("TBD", "handle edge cases", "add appropriate validation", "write tests for the above", a type or
function no task defines) are the opposite failure. The self-review catches both.

## Interfaces between tasks

The implementer sees only their own task. The **Interfaces** block is how they learn the names and
types their neighbors use:

- **Produces:** exact function and type names, parameters and return types, constants with their
  values, error types and when they are raised, file formats, command shapes and exit codes.
- **Consumes:** what this task takes from earlier tasks, named exactly as those tasks produce it.

The manager's pre-flight scan (`apm:executing-plans`) reads these blocks to find every pair of tasks
that touch, so state them even when they look obvious. A name that differs between producer and
consumer (`clearLayers` in Task 3, `clearAllLayers` in Task 7) is a bug in the plan.

## Structural acceptance criteria

The plan ends with a section that lists, concretely, the shape the result must have, each one
checkable:

```
## Structural acceptance criteria (checked before the PR)
- Every file the plan touches is at most 200 lines of logic, every function at most 15,
  measured by `<CLI> metrics`.
- `src/orders/legacy.ext` is under the file limit after Task 2 (it starts at 640).
- The domain layer imports nothing from the storage layer (the profile's layer map).
- `docs/adr/0012-price-tables.md` exists.
- `<CLI> debt check` passes; no existing test was weakened.
```

- These come from the design's constraints and anti-goals, the profile's limits and layer map, and
  the issue. Every document the plan promises (a decision record, a guide) is named by path here,
  and some task writes it.
- The reviewer checks every one, and they are criterion 4 of the merge gate. The manager will not
  merge with one unmet.
- **If a constraint is wrong or too expensive, say so and get a decision.** The planner says so in
  its report; the manager asks the user. Silently dropping it and delivering the features is the
  failure this rule exists to prevent.

## Extract before you add

**When a task touches code already over a limit, a pure-move refactoring task comes first**, as its
own task with its own commit, verified before the task that adds to it.

- Find them with `<CLI> metrics` before you write the tasks.
- The extraction task says what moves where, and that the same tests pass on both sides of it
  unchanged. It names the resulting files, and each lands under the file limit; a split into two
  over-limit files fails the debt ratchet. If the parts cannot get under the limit in this work,
  that is a decision for the user, raised in your report.
- Logic does not move sideways: a decision found in an edge or presentation file moves to tested
  logic, and the extraction task says so.
- The feature task then adds to the smaller piece.

See `apm:refactoring` for the rules the extraction itself follows.

## Allowlisted actions

The approved plan is the allowlist. If any task needs to write a protected path, delete a file, or
run a destructive command, the plan names it here, exactly, with the task that needs it and why:

```
## Allowlisted actions
- Task 4: `--path data/catalog.db`: regenerated by the project's catalog builder; the old
  file is the builder's previous output.
- Task 6: `--command "git rm src/orders/legacy_pricing.ext"`: the file is replaced by Task 5.
```

- Approving the plan approves exactly these and nothing more. The manager records each one with
  `<CLI> allow N --path GLOB --reason TEXT` or `<CLI> allow N --command PREFIX --reason TEXT`.
- Keep each one narrow: one path, not a whole tree; one exact command, not a family of them.
- Anything not named stays blocked. If a worker hits a block the plan did not foresee, the manager
  asks the user for that one action.
- A deletion is also named in the task's **Files** block (`Delete:`), so it happens as a tracked git
  change, never as a side effect.
- If nothing needs allowing, the section says "None."

## Review focus

The header's **Review Focus** lists the input classes or failure modes the design implies, but that
no task's tests exercise, that are most likely to bite a person using the result: up to five, most
likely first, one line each, naming the input or condition and the behavior a reasonable person
would expect. The design is a vision document: it says what the software must do, not everything it
will meet, and its silence on an input is not permission for that input to break the program.

Write the list once, with the design in front of you. Then, for each line, add the test that pins
it to the task that owns the code, and name that task in the line: "Tests are in Task 2 and Task
5." An empty section means you checked and found none, not that you skipped the check. The reviewer
is pointed at this list and checks each line deliberately.

## Self-review

After writing the whole plan, look at the design with fresh eyes and check the plan against it.
This is a checklist the planner runs itself, not a dispatch.

1. **Coverage.** For each section and requirement of the design, point to the task that implements
   it. A requirement with no task gets one.
2. **Step scan.** Every step lets the implementer write exactly one reasonable thing. A line that
   decides nothing is a gap; a function body the signature and tests already determine is a
   transcript. Fix both.
3. **Type consistency.** The names, signatures and types in later tasks match what earlier tasks
   produce.
4. **Review focus.** Each line has its test in the owning task.
5. **Proportion.** A plan several times longer than its design is a transcript of the program. If
   code is most of the document, replace bodies with signatures, test names and assertions, and
   check each step is still unambiguous.
6. **Structure.** Every constraint in the design, the profile and the issue appears as a checkable
   structural criterion, and every promised document has a task that writes it.
7. **Extraction.** Every touched file over a limit has its extraction task first.
8. **Allowlist.** Every protected-path write, deletion or destructive step in any task is listed, and
   nothing else is.
9. **Files.** Every task names its files, and the tasks said to run in parallel share none.

Fix what you find inline; there is no need to re-review. Then report the plan to the manager.

## Handing the plan to the manager

The planner returns its structured report (status, files changed, commands run, concerns, found
elsewhere) with the plan's path and any question only the user can answer.

The manager reads the plan, runs the self-review again quickly, and records it with
`<CLI> issue N --status awaiting-approval --plan PATH`. Then it shows the user a **plan summary**:
the goal, the tasks in order, what will be tested, the structural criteria, the risks, the
allowlisted actions, and a link to the full plan file. The user approves it, edits it, or sends it
back. Only after an explicit approval does the manager record the allowlist with `<CLI> allow` and
start building with `apm:executing-plans`. There is no choice of how to execute: the framework
always builds through the manager's workers.

A plan written before the framework was adopted is not approved until the user approves it under
the framework.

## Common mistakes

- **Structural constraints in the prose but not in the criteria**, so nobody checks them.
- **A feature task that adds to an over-limit file** with no extraction task before it.
- **A promised document with no task** that writes it.
- **Placeholders**: "TBD", "handle errors appropriately", "add tests", a type no task defines.
- **Transcripts**: whole function bodies the tests and signature already determine.
- **Interfaces that drift**: a name or type that changes between the task that produces it and the
  one that consumes it.
- **Tasks without exact files**, so the manager cannot tell whether they may run in parallel.
- **A broad allowlist entry** (a whole directory, a command prefix that matches anything), or a
  destructive step that is in a task but not in the allowlist.
- **Guessing an answer** only the user can give, instead of returning it as a question.
- **Setup, configuration or documentation as their own tasks** when they belong to the task that
  needs them; or one task so large a reviewer cannot judge it.
- **Skipping the review focus**, or listing focus lines with no test in any task.
