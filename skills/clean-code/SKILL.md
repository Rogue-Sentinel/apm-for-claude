---
name: clean-code
description: "Use when you open a file to change it, when you need the function, file or public-method limits and how lines of logic are counted, or when you are about to add code to something already over a limit."
---

# Clean code

Every file you touch leaves cleaner than you found it, and no change makes the debt worse.

## When this applies

- You are about to edit a file, for any reason.
- You need the size limits, or need to know whether a function or file is over them.
- You are about to add lines to a function or file that is already over a limit.
- You are naming something, or a name in the code you are reading made you stop and think.
- A function you are writing is doing more than one thing.
- A reviewer made a "while you're here" suggestion, or you have just finished a feature and are
  deciding what small improvement to leave behind.
- You are working in a codebase with accumulated debt.
- A reader has to read the implementation to understand a name, or a name caused confusion in
  review.

## The core rule

Code is read far more often than it is written, so the working standard is code a stranger can
read in one pass. Concretely: functions and files stay under the limits, names say what things
are, each function does one thing, and every change leaves the debt the same or smaller. These
rules are invoked, not remembered: when a trigger below fires, load the skill it names.

## The limits

| What | Limit | Where the number comes from | When it is exceeded |
|------|-------|-----------------------------|---------------------|
| A function | at most **15 lines of logic** | the extract-method rule and the long-method smell | it is debt, and any growth, or a new one, fails the ratchet |
| A file | at most **200 lines of logic** | the branch-review scorecard | it is debt, and any growth, or a new one, fails the ratchet |
| A type with **7 or more public methods** | needs a stated reason in review | the large-class smell | it is a review flag: the reason is written down where a reviewer sees it |

- The limits are framework defaults. A project overrides them in its profile under
  `standard.limits` (`function`, `file`, `public_methods`), and chooses which files are measured
  under `standard.metrics` (`include`, `exclude`, `extra_exclude`). A project with its own checker
  declares it under `standard.debt_sources`, so its numbers join the ratchet.
- Raising a limit is itself a worsening: the debt check reports "limit loosened" and fails until
  the user accepts it. Never raise a limit to make a number pass.
- Code over a limit is **debt**. It is reported, tracked and paid down; it is never a reason to
  stop work, and never something to hide.
- A wide type (7+ public methods) is not automatically wrong: a facade or a value type with many
  accessors may be right. The rule is that the reason is written down where a reviewer will see it.
  Where the metrics can count public methods, a newly flagged type shows up in the debt check like
  any other new item.

**Measuring.** `<CLI> metrics [--json] [PATH ...]` measures the project against its limits: the
counts of over-limit functions and files, each one as `path:line name -- N lines`, the wide types,
and any file whose functions could not be measured, with the reason. It works in any git
repository, uses the profile's `standard` when there is one and the defaults otherwise, and always
exits 0 (the ratchet is the gate, not the report). `<CLI>` is the framework's command line, as the manager's prompt defines it. Workers
may run `<CLI> metrics` and `<CLI> debt check`, with the exact command line the manager put in
their brief: both only read. **Only the manager runs `<CLI> debt baseline`**; a worker never
does, and the guard denies it. Before you edit a function, know its number.

## Counting lines of logic

A **line of logic** is a line that still holds code after comments, docstrings and preprocessor
lines are removed, and that is not made only of brackets, `;` and `,`.

- **Not counted:** blank lines, comment lines, documentation strings, preprocessor directives, and
  lines holding only `{ } ( ) [ ] ; ,` (a closing `}`, `};`, `});`, `],`).
- **Counted:** every other line, including `} else {`, a line holding only a string (its quotes
  remain once its contents are stripped), and every line of a multi-line string *value* that is not
  a docstring.
- A brace or comment marker *inside* a string is not code, and a brace *inside* a comment is not
  code. Escaped quotes do not end a string.
- A function's count is its **body**: decorators, annotations and the signature (however many
  lines it spans) are not counted. A nested function or lambda counts in its parent too.

Why this definition: putting braces on their own lines and writing the *reasons* in comments are
good habits. Counting raw lines would punish both and push toward deleting the comments that make
code reviewable.

Hand count:

```
function total(order) {          // signature: not counted
  // sum the lines                // comment: not counted
  sum = 0                         // 1
  for line in order.lines {       // 2
    sum = sum + line.price        // 3
  }                               // lone bracket: not counted

  return sum                      // 4
}                                 // lone bracket: not counted
```

**The tool is a heuristic.** `<CLI> metrics` is a scanner, not a compiler. It counts both arms of a
conditional-compilation block (each branch between `#if`, `#else` and `#endif`), because it cannot
know which one builds; only the directive lines themselves are dropped. It does not expand macros,
and a constructor whose initializer list itself uses braces can be misread. Where it disagrees with
a hand count, the fix is a failing fixture for the tool first; a project that needs exactness
declares its own checker in `standard.debt_sources`.

## Debt never grows

**A change may shrink debt but never grow it.** You do not add a line to a function or file that is
already over its limit.

- Over the limit and you need to change it? Extract first, in its own commit, then make your
  change in the smaller piece. Load `apm:refactoring`.
- The ratchet makes this mechanical: `<CLI> debt check` compares the current numbers with the
  recorded baseline and fails on any of these: a total that rose, an over-limit item that grew, a
  new over-limit item, a project checker's number that rose or vanished, or a loosened limit. A
  pure move (the same function, the same size, in another file) is not new debt.
- `<CLI> debt baseline` re-records the numbers; it only ever tightens on its own. Recording a worse
  baseline takes `--accept` with a reason, and only after the user has approved that specific
  worsening. Only the manager runs `<CLI> debt baseline`; workers never write the baseline or the
  profile.
- Debt in code your work touches is paid down in that work, through extract-before-you-add tasks.
  Debt elsewhere becomes a ranked issue for the user to schedule, not a detour.

## The boy scout rule

"Leave the campground cleaner than you found it." When you open a file to change it, make one
small improvement before you leave. Over time these compound, and the code gets cleaner without
dedicated cleanup projects. **The rule covers only code you are already touching**: never tidy
files unrelated to your task.

1. **Make your primary change.** Finish the feature or fix that brought you here; it works and
   its tests pass.
2. **Scan for a quick win** in the code you just touched or read: a name that could be better, a
   block that could be extracted, a comment that is redundant or out of date, dead code, an unused
   import.
3. **Apply one improvement** (two at most). It is small, low risk, and takes under five minutes.
4. **Verify.** Run the tests. The improvement must not change behavior; if it does, it is not a
   cleanup at all, and it goes back out until it can be done as a proper refactoring.
5. **Commit it on its own.** A boy scout improvement (a rename, an extraction, deleting dead code)
   is a refactoring, and **refactoring and behavior never share a commit**: there is no exception
   for small ones. Commit it before or after the behavior change, never inside it, with a message
   that says what it is: "Rename the ambiguous `d` to `elapsedDays`."

Signs the rule is not being followed: small quality issues that survive for months because "it's
not my task"; quality that slowly degrades; files people avoid because they are messy; review
comments like "this name is confusing, but it's out of scope"; debt that grows with no effort to
reduce it.

Example. Primary change: add a validation rule. Pick one of: rename `val` to `validationResult`;
delete the commented-out block above; delete the unused import; fix the misleading comment; extract
the duplicated validation into a helper.

The per-item checklist with time budgets and safety rules is in
[references/improvement-checklist.md](references/improvement-checklist.md).

## Meaningful names

A name tells you why a thing exists, what it does and how it is used. **If a name needs a comment to
explain it, the name is wrong.** Good names cut documentation and make change safer, because intent
is explicit.

1. **Find the violations:** single letters outside trivial loop counters (`x`, `d`, `t`);
   abbreviations (`usr`, `mgr`, `btn`, `cfg`); generic names (`data`, `info`, `temp`, `result`,
   `obj`, `val`, `manager`, `handler`); misleading names (`isEnabled` that means `isVisible`); names
   that no longer match the behavior; types encoded in names (`userList`, `nameString`); encoded
   prefixes (`m_name`, `str_value`, `i_count`).
2. **Understand the purpose.** Read how it is used. Name it in the domain's language, not the
   mechanism's.
3. **Choose the name.** Nouns for variables and types, verbs for functions, a predicate phrase for
   booleans. Be specific: `customerEmailAddress` over `email`, `isExpired` over `flag`. Units go in
   the type or the name (`timeoutMs`, `distanceMeters`).
4. **Rename everywhere** with the editor's rename refactoring or a checked search: tests,
   configuration, documentation and API boundaries included.
5. **Verify.** Run the tests, confirm nothing was missed, and read the new name in context.

| Before | After | Why |
|--------|-------|-----|
| `d` | `elapsedDays` | reveals meaning |
| `list` | `activeUsers` | names the content |
| `flag` | `isEligibleForDiscount` | describes the condition |
| `doIt()` | `sendWelcomeEmail()` | names the action |
| `DataManager` | `OrderRepository` | names the domain role |
| `process()` | `calculateShippingCost()` | names the computation |

The rules by kind of identifier, the consistency table and the domain-language rule are in
[references/naming-conventions.md](references/naming-conventions.md). Renaming as a refactoring is
in `apm:refactoring`.

## Functions do one thing

A function does one thing, at one level of abstraction, and its name says what that thing is.

- **One level of abstraction.** A function either orchestrates (calls well-named steps) or does a
  detail (arithmetic, a loop over items). Mixing the two is the signal to extract.
- **A comment that explains what the next block does is a function name waiting to happen.**
  Extract the block and let the name replace the comment. Comments that explain *why* stay.
- **"And" in the name means two things.** `validateAndSave` is two functions.
- **If you cannot name it, you do not yet know what it does.** Find out before you extract.
- **Few parameters.** Zero to two is good, three is acceptable but consider a parameter object,
  four or more means the function needs decomposing.
- **No hidden effects.** A function named as a question does not change state; one that changes
  state says so in its name.
- **Shallow nesting.** Three or more levels of indentation is a candidate for extraction or guard
  clauses.

How to get there is `apm:refactoring` (extract method); spotting where it went wrong is
`apm:code-smells`.

## Which skill, when

| Trigger | Load |
|---------|------|
| Before any new behavior or fix | `apm:test-first` |
| On touching a file | `apm:clean-code` (this skill) |
| A function or file you touch is over a limit, or a change touches debt | `apm:refactoring` |
| Adding or changing a type or module | `apm:solid`, `apm:object-design` |
| Crossing a layer or adding a dependency | `apm:clean-architecture` |
| Absence, failure, state, time or randomness | `apm:functional-core` |
| Reviewing or auditing code | `apm:code-smells` |
| Making a decision a later reader would question | `apm:adr` |

## Idioms worth carrying

These hold in every language; a project adds its own in its profile.

- **Absence is a value, never a sentinel.** Not `0`, not `-1`, not an empty string meaning
  "none". See `apm:functional-core`.
- **The clock is a parameter.** Logic that depends on the time takes the time as an input, so a
  test can set it.
- **Units go in the type or the name.**
- **Ownership is explicit.** Every resource has one owner that releases it; nothing relies on a
  reader remembering to.
- **A decision never lives at the edge.** The entry points and the presentation layer forward and
  draw; the choices live in tested logic behind them. See `apm:clean-architecture`.

## References

- [references/improvement-checklist.md](references/improvement-checklist.md): the boy scout
  checklist, safety rules and examples.
- [references/naming-conventions.md](references/naming-conventions.md): naming rules by identifier
  kind, consistency and domain language.

## Common mistakes

- **Adding "just one line"** to a function that is already over. That is growing debt; extract first.
- **Raising a limit in the profile** to make a number pass. It is reported as a loosened limit and
  fails the ratchet.
- **Folding a cleanup into the behavior commit**, however small. It gets its own commit.
- **Too many cleanups in one pass.** One or two per file; anything bigger is its own task.
- **Cleaning files you did not need to touch.** Scope creep, and noise in the review.
- **A cleanup that changes behavior.** Then it is not a cleanup: back it out, and make the behavior
  change test-first in its own commit if it is wanted at all.
- **Skipping the tests** after a cleanup because it "obviously" changed nothing.
- **Using the boy scout rule** to justify a large refactoring inside a feature change.
- **Names that are too long** (`theListOfAllActiveUserEmailAddresses`): specific, not exhaustive.
- **Synonyms for one operation** (`fetch`, `get`, `retrieve` side by side).
- **Renaming without updating every reference**, tests included.
- **Counting raw lines** instead of lines of logic, or trusting the tool over a careful hand count
  without writing the fixture that settles it.
