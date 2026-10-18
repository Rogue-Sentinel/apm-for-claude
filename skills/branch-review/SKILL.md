---
name: branch-review
description: "Use when a branch needs a scored quality review against its base, when old code is being compared with its replacement, when deciding whether a branch is ready to merge, or when tracking how a branch's quality changed across repeated reviews."
---

# Branch review

Compare the old code on the base branch with the new code on the feature branch, and produce an
evidence-backed scorecard across eleven quality dimensions.

## When this applies

- A feature branch has changes ready for review, and someone wants to know how good they are.
- Old code is being replaced: a migration, a rewrite, or a move to a new architecture or approach.
- Someone asks for a scored quality assessment, or a code quality scorecard.
- You are deciding whether a branch is ready to merge, or there is a worry that quality is
  regressing during a change.
- A team wants objective numbers on branch readiness rather than impressions.
- The branch has been reviewed before, and you are tracking its progress across iterations.

## The core rule

**Measure quality with evidence, not impressions.** Score every dimension for the old code and the
new, and back every number with file names, line counts, pattern counts and concrete examples.
Honest, specific scores with a path to improve are worth more than generous ones. Architecture, type
and contract safety, and testing weigh more than the rest, because their effects compound over time,
so the overall score is a weighted judgment and **not an average**.

## Gather evidence

Use `git diff`, `git grep`, file listings and file reads. Never guess a number; if you cannot
measure something, say so in the evidence instead of estimating it.

1. **Identify the branch and its base.** Use the branch you were given, otherwise the current
   branch. The base is the branch the work was cut from, which is the one you were given as the
   base. Only when none was given do you fall back to the project's main branch (`main` or
   `master`, unless the project says otherwise). Every command below uses that same `<base>`,
   `apm debt check --base <base>` included.
2. **Read the change.**
   - `git diff <base>...HEAD --stat` lists every changed file.
   - `git diff <base>...HEAD` shows the changes themselves.
   - Then read the changed files whole, not only their hunks: a diff without the context around it
     misleads.
3. **Measure the sizes.** `apm metrics` lists every function and file over the profile's limits
   (`standard.limits`: by default 15 lines of logic per function, 200 per file, and a wide-class
   flag at 7 or more public methods), each as `path:line name -- N lines`. `apm metrics --json`
   gives every number. Run it on the branch for the new side. For the old side, use the baseline recorded on
   the base (`git show <base>:.apm/debt.json`), or `apm metrics` run in a separate checkout of the
   base. A worker asks the manager for that checkout; a review never creates or removes worktrees.
   Flag every changed file over the file limit.
4. **Run the ratchet.** `apm debt check --base <base>` compares the current numbers with the
   recorded baseline. Exit 0 means no debt grew. Exit 1 means something got worse, and it prints
   each regression: a total that rose, an over-limit item that grew, a new over-limit item, a
   checker's number that rose, a loosened limit, or a baseline loosened against `<base>` with no
   new acceptance recorded. Exit 2 means there is no baseline, which is itself a finding. Workers
   may run `apm metrics` and `apm debt check`, because both only read.
   **Only the manager runs `apm debt baseline`**, and a review never does: a review reports the
   numbers and changes none of them.
5. **Count the patterns for each dimension**, on both sides. `git grep -c -E '<pattern>' <base> --
   <pathspec>` counts on the base without a checkout, and the same command without `<base>` counts
   on the branch. The neutral checks are under each dimension below. The concrete patterns for each
   language are in [references/evidence-by-language.md](references/evidence-by-language.md), and a
   project adds its own under `standard.review_patterns` in its profile. Report the count of every
   project pattern under the dimension it names.
6. **Decide whether the project has a user interface.** The profile's `standard.ui` holds the
   answer: `true`, `false`, or absent.
   - **`true` or `false` decides.** If the code contradicts it (a profile that says `false` over
     code that draws screens, or `true` over a library with nothing to show), score by the profile
     and report the contradiction as a profile finding for the manager.
   - **Absent:** decide from the code, and put the evidence in the N/A reason: "N/A (no user
     interface: no drawing, window or markup code under `src/`)".

   Without a user interface, the UI-scoped parts of the scorecard are scored N/A with that reason
   (see [The scorecard](#the-scorecard)).
7. **Look for a previous review** (see [Previous reviews](#previous-reviews)).

How to gather and present the evidence for each dimension, with an example of each, is in
[references/scoring-evidence-guide.md](references/scoring-evidence-guide.md).

## The scorecard

Rate each dimension from 1 to 10 for the old code and the new.

**Placing a score within a band.** First find the band whose whole description the code meets; the
band above it is the one it does not yet meet. Then place the score within the band by how much of
the next band's description is already true: none of it is the bottom of the band (1, 4 or 7),
some of it the middle (2 or 5), most of it the top (3, 6 or 8). For 9-10, 9 meets the band and 10
meets it with nothing left to name in "what still needs work". The evidence says which items of the
next band are met and which are not, so a reader can check the placement.

Two kinds of score are N/A rather than a number:

- **Greenfield.** If the old code does not exist, the old column is N/A and only the new code is
  rated.
- **No user interface.** Styling and presentation, accessibility, and the user-navigation half of
  entry points and routing are UI-scoped: they apply only to code that has a user interface.
  Without one, the first two are N/A with the reason written in the cell, "N/A (no user
  interface)", and entry points and routing is scored on its entry points alone. An N/A dimension
  leaves the overall score; it does not count as a zero or as a ten.

The weight of each dimension is in [Weighting the overall score](#weighting-the-overall-score).

### Type and contract safety

Whether the program's values have types or contracts that a tool checks, and whether the code
escapes them. In a statically typed language this is the type system and the casts that defeat it;
in a dynamically typed one it is type annotations and a checker, and the validation of every value
that crosses a boundary.

Look for: the strictest checking mode the toolchain offers, and whether it is on; casts and
conversions that bypass the checker (to the top type, or through it to another type); comments or
attributes that suppress a checker's diagnostics; maps from strings to untyped values standing in
for a real type; inputs from outside the program used without being validated.

| Score | What it looks like |
|-------|--------------------|
| 1-3 | No types or contracts, or the top type everywhere |
| 4-6 | Partial types, with casts to get past the checker |
| 7-8 | Strict checking on, few casts |
| 9-10 | Complete types, generic utilities, no unsafe casts |

### State management

Where state lives, who may change it, and how changes reach the code that depends on them.

Look for: how many layers a value is passed through only to reach the one that uses it; global or
shared mutable state, and who writes it; reusable units that own a piece of state (stores, view
models, state hooks) and how many there are; derived values stored and kept in sync by hand rather
than computed; expensive derivations recomputed on every change.

| Score | What it looks like |
|-------|--------------------|
| 1-3 | Global mutations, no pattern |
| 4-6 | Basic state: hooks or fields held where they are used, ad hoc |
| 7-8 | A proper state owner or library, little pass-through of values |
| 9-10 | Memoized selectors, derived state computed rather than stored, change notification (signals or observers) |

### Module architecture

How the code is divided into modules, files and types, and whether each has one job. A module's
imports are checked against the profile's layer map when it declares one (see
`apm:clean-architecture`).

Look for: the over-limit files and functions from `apm metrics`; the largest files; how many
exported units each file holds; imports that point the wrong way across a layer; decisions living in
the entry points or the presentation layer instead of in tested logic.

| Score | What it looks like |
|-------|--------------------|
| 1-3 | Monolithic files of 1000+ lines |
| 4-6 | Some splitting, but large files remain |
| 7-8 | Most files under the file limit (200 lines of logic by default), clear separation |
| 9-10 | Composable, single-responsibility modules, files well under the limit (150 lines at the default) |

### Entry points and routing

How control enters the program and reaches the code that handles it. Every program has entry
points: its main function, command-line subcommands, request handlers, message or event handlers,
callbacks from a host. A program with a user interface also has navigation: the screens or pages,
and how the user moves between them. **This dimension is never wholly N/A.** Only its navigation
half is UI-scoped: without a user interface that half is "N/A (no user interface)",
the entry points are still scored, and the score rests on them alone. With a user interface,
each half gets a band, and the dimension's score is the lower of the two.

Look for: one dispatch place, or dispatch scattered through the code; entry points that only
forward, or that make decisions themselves; unknown commands, routes or messages handled; for
navigation, screens loaded on demand (lazy loading, code splitting), nested layouts, prefetching,
not-found and error routes, breadcrumbs.

| Score | What it looks like |
|-------|--------------------|
| 1-3 | No routing (every move is a full reload), or dispatch scattered and making decisions at the edge |
| 4-6 | Basic routing; entry points exist but hold logic |
| 7-8 | Thin entry points that forward to tested logic; lazy loading, nested layouts |
| 9-10 | Code splitting, prefetching, not-found and error routes, breadcrumbs; unknown input handled at every entry point |

### Styling and presentation

How the look of a user interface is defined. UI-scoped: without a user interface this dimension is
"N/A (no user interface)".

Look for: literal style values (colors, sizes, spacing) written inline where things are drawn,
against styles kept in one named place (stylesheets, style modules, a theme); a design token
system, and whether the code uses it consistently; one very large style file that everything
depends on; whether the look can be themed.

| Score | What it looks like |
|-------|--------------------|
| 1-3 | All inline, or massive style files |
| 4-6 | A mix of inline styles and shared style modules |
| 7-8 | Style modules or tokens, few inline styles |
| 9-10 | A design token system, zero inline styles, themeable |

### Testing

Whether the behavior is pinned by tests that would fail if it broke (see `apm:test-first`).

Look for: the number of test files against the number of source modules; the number of test cases;
unit, integration and end-to-end tests, and shallow tests that only check that something runs or
renders; tests for the parts of a screen, and accessibility assertions where there is a user
interface; skipped or disabled tests; whether tests arrived in the same commits as the behavior they
cover.

| Score | What it looks like |
|-------|--------------------|
| 1-3 | No tests |
| 4-6 | Shallow smoke tests only |
| 7-8 | Behavior tests, good coverage, some integration tests |
| 9-10 | Integration and end-to-end tests; tests for each part of a screen and accessibility tests (where there is a user interface) |

Without a user interface, the screen and accessibility parts of the 9-10 band do not apply, so a
command-line tool or a library reaches 9-10 on integration and end-to-end tests alone.

### Error handling

What happens when something fails, and whether the user or the caller hears about it (see
`apm:functional-core`).

Look for: failures that can reach the top unhandled and crash the program; catch blocks that
swallow an error silently; a boundary at each major part that contains a failure (for a user
interface, an error boundary per screen or route segment); errors with types, or failure returned as
a value; calls to the outside world with no failure path; loading, error and empty states each
handled where data is shown; retries, graceful degradation, and monitoring or logging of failures.

| Score | What it looks like |
|-------|--------------------|
| 1-3 | Unhandled errors crash the program |
| 4-6 | Basic try and catch |
| 7-8 | Error boundaries, typed errors, feedback to the user |
| 9-10 | Retry logic, graceful degradation, monitoring |

### External integration

How the code talks to anything outside it: network services, a host application or its SDK,
databases, files, other processes.

Look for: raw calls to the outside scattered through the code, against one wrapper or adapter per
outside system; failure handling on every call; timeouts and cancellation (a call that outlives the
code waiting for it); types on what comes back, and validation of it; caching; retries; pagination;
optimistic updates.

| Score | What it looks like |
|-------|--------------------|
| 1-3 | Raw calls, no error handling |
| 4-6 | A wrapper with basic error handling |
| 7-8 | Typed responses, caching, cancellation |
| 9-10 | Retry, pagination, optimistic updates |

### Accessibility

Whether everyone can use the user interface: with a keyboard alone, with a screen reader, and
without relying on color. UI-scoped: without a user interface this dimension is
"N/A (no user interface)".

Look for: accessible names and roles on controls; semantic structure (landmarks, headings, lists)
rather than generic containers; status shown by color alone with no text or shape alternative;
keyboard navigation and visible focus; screen-reader support; accessibility tests; conformance to
WCAG AA, or the platform's own accessibility guidelines.

| Score | What it looks like |
|-------|--------------------|
| 1-3 | No accessible names or roles, no semantic structure |
| 4-6 | Some accessible labels |
| 7-8 | Keyboard navigation, screen-reader support, semantic structure |
| 9-10 | WCAG AA compliant, accessibility tests |

### Code duplication

Whether each piece of knowledge lives in one place (see `apm:code-smells`, duplicate code).

Look for: constants repeated across files (a base address, a limit, a color); copy-pasted units of
the user interface or of logic; helpers duplicated in several modules; shared patterns not yet
extracted into a reusable unit; a shared unit that exists while one-off copies of it are still
written.

| Score | What it looks like |
|-------|--------------------|
| 1-3 | Extensive copy-paste |
| 4-6 | Some shared utilities |
| 7-8 | Centralized constants, shared components or shared modules |
| 9-10 | DRY: shared reusable units (hooks, helpers) and a component library, or a library of shared modules where there is no user interface |

### Developer experience and maintainability

How easy the project is to work on safely: the tooling that catches mistakes before a person does.

Look for: a linter and a formatter, configured and passing; pre-commit hooks; import sorting rules;
import path aliases; continuous integration that runs the tests, the linter, `apm metrics` and
`apm debt check`; automatic fixing; consistent conventions; documentation for a newcomer.

| Score | What it looks like |
|-------|--------------------|
| 1-3 | No tooling |
| 4-6 | Basic linting |
| 7-8 | Lint, format, pre-commit hooks and path aliases |
| 9-10 | Checks in continuous integration, automatic fixing, consistent conventions, documentation |

## Weighting the overall score

The overall score is **not an average** of the eleven. Architecture, type and contract safety, and
testing compound: every later change is cheaper or dearer because of them. So they weigh most:

| Weight | Dimensions |
|--------|------------|
| High | Type and contract safety, Module architecture, Testing |
| Medium | Error handling, State management, External integration, Accessibility, Code duplication |
| Low | Entry points and routing, Styling and presentation, Developer experience and maintainability |

A project with 9/10 type and contract safety, 9/10 testing and 4/10 styling is in better shape than
one with 9/10 styling, 4/10 type and contract safety and 4/10 testing. State the overall as a whole
number and give the reason for it in the bottom line. As a check on yourself, a weighted mean
(high 3, medium 2, low 1, N/A left out) should land near your overall; if it does not, the bottom
line says why.

## Previous reviews

Look for `BRANCH_REVIEW.md` at the repository root or in the `.claude/` directory. If one exists,
the scorecard gains a **Previous New** column holding that review's new-code score for each
dimension, so the report shows the branch's progression, and the bottom line names all three
scores (see [Report](#report)).

A reviewer returns the report and writes no file. The manager decides whether to keep it for the
next review; when it is kept, it is committed as `BRANCH_REVIEW.md` at the repository root.

A previous review may use the older dimension names. Read them as these:

| Older name | Dimension |
|------------|-----------|
| Type Safety | Type and contract safety |
| Component Architecture | Module architecture |
| Routing | Entry points and routing |
| Styling | Styling and presentation |
| API Integration | External integration |
| DX & Maintainability | Developer experience and maintainability |

The others (State management, Testing, Error handling, Accessibility, Code duplication) are
unchanged.

## Report

Produce the report in this shape. Every cell holds a score and its evidence; every verdict says what
changed and where.

```
## [Old approach] vs [New approach]: review

### Measurements
- apm metrics: functions over the limit N -> M, files over the limit N -> M, wide classes N -> M
- apm debt check --base <base>: exit 0 / 1 (each regression) / 2 (no baseline)

### Scorecard

| Dimension | Old | New | Verdict |
|---|---|---|---|
| **Type and contract safety** | X/10 (evidence) | X/10 (evidence) | Verdict: specific details |
| **State management** | X/10 (evidence) | X/10 (evidence) | Verdict: specific details |
| **Module architecture** | X/10 (evidence) | X/10 (evidence) | Verdict: specific details |
| **Entry points and routing** | X/10 (evidence) | X/10 (evidence) | Verdict: specific details |
| **Styling and presentation** | X/10 (evidence) | X/10 (evidence) | Verdict: specific details |
| **Testing** | X/10 (evidence) | X/10 (evidence) | Verdict: specific details |
| **Error handling** | X/10 (evidence) | X/10 (evidence) | Verdict: specific details |
| **External integration** | X/10 (evidence) | X/10 (evidence) | Verdict: specific details |
| **Accessibility** | X/10 (evidence) | X/10 (evidence) | Verdict: specific details |
| **Code duplication** | X/10 (evidence) | X/10 (evidence) | Verdict: specific details |
| **Developer experience and maintainability** | X/10 (evidence) | X/10 (evidence) | Verdict: specific details |

### What got better
1. A concrete improvement, with its evidence (file names, line counts, patterns).

### What got worse (or what still needs work)
1. A regression or a remaining issue, with its evidence.

### Bottom line
Two or three honest sentences.
**The old code was X/10. The new code is Y/10.**
```

With a previous review, the scorecard uses five columns:

```
| Dimension | Old | Previous New | Current New | Verdict |
|---|---|---|---|---|
```

and the report ends with:
**The old code was X/10. The previous new code was Y/10. The current new code is Z/10.**

An N/A cell names its reason: "N/A (greenfield)" or "N/A (no user interface)". On a greenfield
branch the bottom line reads "The old code was N/A (greenfield). The new code is Y/10."

## Scoring honestly

- **Be honest and specific.** Back every score with file names, line counts or pattern counts.
- **Do not inflate.** A 5/10 with a clear path to improve is more useful than a generous 7/10.
  Inflating a score to avoid a difficult conversation fails the reader who has to act on it.
- **Never guess.** Use `git diff`, `git grep`, `apm metrics`, `apm debt check`, file listings and
  file reads. Report the numbers the commands printed, not the ones you expected (see
  `apm:verification`).
- **If the old code does not exist (greenfield), score the old as N/A** and rate only the new code.
- **The overall score is not an average.** Weigh architecture, type and contract safety, and testing
  more heavily, because they compound.
- **Compare with the base.** A 6/10 that was a 3/10 is great progress; a 7/10 that was a 9/10 is a
  regression, and both belong in the verdict.
- **Read the context.** A diff alone hides how the changed code fits the files around it.
- **N/A is a finding, not a gap.** Give its reason, and never use it to dodge a dimension that does
  apply.

## References

- [references/scoring-evidence-guide.md](references/scoring-evidence-guide.md): how to gather and
  present the evidence for each dimension, with an example of each, and the overall weighting.
- [references/evidence-by-language.md](references/evidence-by-language.md): the concrete patterns
  per language, and how a project adds its own under `standard.review_patterns`.

## Common mistakes

- **Inflating scores** to avoid a difficult conversation.
- **Scoring without evidence.** Every number needs file names, counts or patterns.
- **Averaging the dimensions equally.** Weigh architecture, type and contract safety, and testing
  higher.
- **Ignoring the base branch.** The comparison is the point: progress and regressions both show only
  against the old code.
- **Reviewing only the diff** without understanding the broader context of the changed files.
- **Counting by eye** what `apm metrics` measures.
- **Running `apm debt baseline` during a review.** A review reports the numbers; only the manager
  records a baseline.
- **Scoring a UI-scoped dimension for code with no user interface**, or marking a dimension N/A that
  does apply, or leaving out the reason. Entry points and routing is never wholly N/A.
- **Overriding the profile's `standard.ui`** because the code seems to disagree. Score by the
  profile and report the contradiction.
- **Comparing with `main`** when the work was cut from another branch. The base is the branch you
  were given, and `apm debt check --base` gets the same ref.
- **Committing `BRANCH_REVIEW.md` yourself.** Return the report; the manager decides whether it is
  kept.
- **Using one language's patterns on another.** Take the patterns for the project's languages from
  the evidence reference, plus the project's own.
