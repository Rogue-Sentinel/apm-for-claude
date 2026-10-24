# APM — Restore the clean-code skills' trigger phrases, nuances and thresholds — Implementation Plan

> **For agentic workers:** the manager builds this plan task by task. Each task is built
> test-first by one implementer in its own worktree and verified by the manager with the task's
> targeted tests. The whole branch is reviewed once at the end, and the full suite runs exactly
> once, through the merge gate, right before the PR. No task touches a safety-critical path, so no
> task gets its own review. Tasks 1 and 5 are run by the manager (subagent scenarios), not by an
> implementer. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put back what the rewording of the 21 clean-code skills and 2 commands lost: the original
trigger phrases in nine skill descriptions, a handful of nuances and thresholds, and the original
library and language names as examples. Our skills otherwise stay as they are.

**Architecture:** Additions only, inside `skills/`. Trigger phrases go into each description as one
appended sentence. Language- and library-specific names go into a new
`references/examples-by-language.md` per skill, linked from the generic wording they illustrate.
Every addition is pinned by an assertion in the skill test file that already covers that skill.

**Tech Stack:** Markdown skills; Python 3 tests run with `python -m pytest -q`. Markdown is not
measured by `<CLI> metrics`.

**Spec:** issue #34 and the manager's brief (no design document; the user ruled: keep our skills as
they are, restore only the missing nuances, thresholds and trigger phrases).

## Source material (read-only)

helmedeiros/clean-code-skills @ `b9805c9`, vendored verbatim at
`C:/Users/darby/source/repos/VirtualAirline Plugin for XP12/.claude/skills/` and `.../.claude/commands/`.
**Never modify anything in that repository.** Read it only to copy an original name or phrase.

## Global Constraints

- **Add, do not reword.** Existing sentences stay word for word except where a task below names the
  exact replacement. No heading is renamed, moved or removed (the coverage inventory and the skill
  tests anchor to headings).
- **Descriptions:** quoted, start with `"Use when`, at most 1024 characters. The existing text stays
  verbatim; the task appends exactly one sentence, starting `Also use when`, before the closing quote.
- **Language-agnostic skills:** a library, product or language name from the originals goes only in a
  file named `references/examples-by-language.md` (the rule in `apm:writing-skills`; `React` is on the
  banned list in `tests/test_skills.py`). The generic wording gets a relative link to that file
  beside it. Pseudo-code examples stay pseudo-code.
- **By-language files:** an H1 `# Examples by language`, one sentence saying they hold the names the
  original skills used, then a table `| Generic wording | Language or ecosystem | Original example |`.
  Only the originals' names, each labeled with its language; nothing invented. Link only to sibling
  files. Each is linked from its skill's `SKILL.md` `## References` list.
- **The class-size signal**, wherever it is added, contains both `about 200 lines` and
  `judged by the reviewer, not measured`. It does not change any limit `<CLI> metrics` enforces.
- American spelling under `skills/`; runnable text says `<CLI> <verb>`, never a bare `apm <verb>`.
- Every test file touched stays at most 200 lines of logic and every function at most 15 (now:
  `tests/test_skills.py` 113, `tests/test_skills_clean_code.py` 63, `tests/test_skills_design.py` 43,
  `tests/test_skills_review.py` 129, `tests/test_docs.py` 134, largest function 13).
- Do not touch `tests/test_guard.py`, `tests/test_cli.py`, `scripts/apm/guard*.py`, `scripts/hook_*.py`,
  `hooks/**`, `.apm/`, or the VirtualAirline repository.
- No version bump: releases are their own issues (#17, #25, #30).
- Workers invoke `apm:writing-skills` and `apm:test-first` before editing a skill.

## Review Focus

1. **Over-triggering between neighbors.** "Code quality" now appears in `code-smells`,
   `branch-review` and (already) `clean-code-audit`; "open-closed" in `solid` and `refactoring`. A
   request phrased the original way should still reach the skill it reached in the originals. Checked
   by the retrieval runs in Tasks 1 and 5.
2. **A name leaking out of a by-language file** into generic text (only `React` and a few others are
   banned by test). Tests are in Task 2 (`instanceof` in `refactoring`) and Task 3 (the four design
   skills).
3. **The class-size signal read as a new measured limit.** A reviewer or auditor could start failing
   files on it. Each of the four places says it is judged, not measured; tests are in Tasks 2, 3 and 4.
4. **The "passes at once" rule applied to a bug-fix regression test.** Restoring "delete it" could
   be read as deleting a regression test that passes before the fix; `## A bug fix starts with a
   failing test` already says such a test must fail first, so the two do not conflict. The reviewer
   reads both sections together. Test is in Task 2.

---

## File Structure

```
skills/clean-code/SKILL.md                         description sentence (Task 2)
skills/code-smells/SKILL.md                        description sentence; class-size signal (Task 2)
skills/code-smells/references/smell-catalog.md     class-size signal under ### Large class (Task 2)
skills/refactoring/SKILL.md                        description; extract-method trigger, ~10 lines, "read like prose"; link (Task 2)
skills/refactoring/references/examples-by-language.md   NEW: `instanceof` (Task 2)
skills/test-first/SKILL.md                         description; "passes at once" agrees with cycle-steps (Task 2)
tests/test_skills.py                               description length cap (Task 2)
tests/test_skills_clean_code.py                    Task 2 assertions
skills/solid/SKILL.md                              description; links beside LSP and DIP signs (Task 3)
skills/solid/references/srp-indicators.md          class-size signal (Task 3)
skills/solid/references/examples-by-language.md    NEW: LSP and DIP names (Task 3)
skills/object-design/SKILL.md                      description; link beside the string-form mistake (Task 3)
skills/object-design/references/composition-patterns.md   links beside delegation, mixins, framework base types (Task 3)
skills/object-design/references/examples-by-language.md   NEW (Task 3)
skills/clean-architecture/SKILL.md                 description; link beside the ports-and-adapters signs (Task 3)
skills/clean-architecture/references/port-adapter-anatomy.md   link under ## Adapters (Task 3)
skills/clean-architecture/references/anti-corruption-layer.md  link in the extension-functions row (Task 3)
skills/clean-architecture/references/examples-by-language.md   NEW (Task 3)
skills/functional-core/SKILL.md                    description; hot-path pitfall; link (Task 3)
skills/functional-core/references/purity-rules.md  links beside impure reads and immutable updates (Task 3)
skills/functional-core/references/examples-by-language.md      NEW (Task 3)
skills/CREDITS.md                                  one sentence: where the original names are kept (Task 3)
tests/test_skills_design.py                        Task 3 assertions
skills/branch-review/SKILL.md                      description; class-size signal (Task 4)
tests/test_skills_review.py                        Task 4 assertions
```

Ruling-dependent tasks (6 to 11) add files only if the user rules that way; each lists its own.

## Order and parallelism

Task 1 (manager) runs first, before any description changes. **Tasks 2, 3 and 4 touch disjoint files
and may run in parallel.** Task 5 (manager) runs after 2, 3 and 4 are merged. Ruling-dependent tasks
run after the task whose files they share: 7 after 2; 8 after 3; 9 after 2 and 3; 10 after 4; 11 has no
shared files and may run alongside anything. Task 12 is last.

---

### Task 1: Retrieval baseline (manager-run, no files change)

The behavioral test for the trigger phrases (`apm:writing-skills`, "Testing with subagents"). Run it
**before** Tasks 2 to 4 change any description.

- [ ] **Step 1:** Dispatch one `general-purpose` subagent with: every framework skill's name and
  description as they are on `main` (37785bf), and these nine requests, asking for the one skill it
  would load first for each, or "none", and why. It takes no other action.
  1. "Does this class break SRP? It has several reasons to change."
  2. "Should we favor composition over inheritance here? The base class is fragile."
  3. "Restructure this as hexagonal architecture, ports and adapters."
  4. "Apply the boy scout rule while you're in this file."
  5. "Give me a systematic assessment of our technical debt."
  6. "Replace these try-catch blocks with a Result type."
  7. "Break up this long function."
  8. "Let's do TDD on this: red-green-refactor."
  9. "Give me a code quality scorecard for this branch."
  Expected skills, in order: `solid`, `object-design`, `clean-architecture`, `clean-code`,
  `code-smells`, `functional-core`, `refactoring`, `test-first`, `branch-review`.
- [ ] **Step 2:** Record each answer, word for word for the misses, in a `## Retrieval check`
  section at the end of this plan (the manager commits the amendment). A baseline with no misses is
  recorded as such; the user's ruling still restores the phrases (see Concerns in the report).

### Task 2: Code skills (clean-code, code-smells, refactoring, test-first)

**Files:**
- Modify: `skills/clean-code/SKILL.md` (description only)
- Modify: `skills/code-smells/SKILL.md` (description; `## Finding smells`)
- Modify: `skills/code-smells/references/smell-catalog.md` (`### Large class`)
- Modify: `skills/refactoring/SKILL.md` (description; `## When this applies`; `## Extract method`;
  `## Replace conditional with polymorphism`; `## References`)
- Create: `skills/refactoring/references/examples-by-language.md`
- Modify: `skills/test-first/SKILL.md` (description; `## Red, green, refactor`, the Red bullet)
- Test: `tests/test_skills_clean_code.py`, `tests/test_skills.py`

**Interfaces:**
- Produces: `skills/refactoring/references/examples-by-language.md` (Task 9 does not use it).
- Produces: in `tests/test_skills_clean_code.py`, a `TRIGGERS` dict and a module-level helper
  `_names_term(text: str, term: str) -> bool` (case-insensitive; `(?<!\w)` before a term that starts
  with a word character and `(?!\w)` after one that ends with one, as `_term_pattern` in
  `tests/test_skills.py`). Tasks 7 and 9 add to this file after this task.

- [ ] **Step 1: Write the failing tests** in `tests/test_skills_clean_code.py`:
  - `test_description_names_the_original_triggers[name]`, parametrized over `TRIGGERS`; every term
    is found in the frontmatter description with `_names_term`:
    - `clean-code`: `boy scout rule`, `leaving code cleaner`, `continuous improvement`,
      `incremental quality improvements`, `improving naming`, `meaningful names`,
      `naming conventions`, `misleading identifiers`
    - `code-smells`: `code smells`, `technical debt`, `reviewing code quality`,
      `systematic code quality assessment`
    - `refactoring`: `break up a long function`, `reduce method length`, `decompose complex logic`,
      `simplify a function`, `complex branching`, `long if-else or switch-case chains`,
      `Open-Closed to branching`
    - `test-first`: `TDD`, `test-driven development`, `writing tests first`,
      `test-first development`, `testable by design`, `red-green-refactor`,
      `incrementally with tests`, `arrange-act-assert`, `AAA`, `given-when-then`,
      `organizing test code`, `test readability`
  - `test_extract_method_keeps_the_original_trigger_threshold_and_aim`: `## When this applies` of
    `refactoring` contains `simplify or decompose a function` and `about 10 lines of logic`;
    `## Extract method` contains `read like prose`.
  - Add `"examples-by-language.md"` to `REFERENCES["refactoring"]` (the existing
    `test_skill_has_its_named_references` then fails).
  - `test_type_checks_point_at_their_examples_by_language`: the new file contains `` `instanceof` ``;
    `## Replace conditional with polymorphism` contains `references/examples-by-language.md`; no
    other `.md` file under `skills/refactoring/` contains `instanceof`.
  - `test_a_test_that_passes_at_once_is_deleted_as_redundant`: `## Red, green, refactor` of
    `test-first` contains `redundant` and `delete it and pick a different behavior`, and does not
    contain `fix or delete`; `references/cycle-steps.md` contains
    `delete it and pick a different behavior`.
  - `test_large_class_has_a_reviewer_judged_class_size_signal`: `## Finding smells` of
    `code-smells`, and `### Large class` of `references/smell-catalog.md`, each contain
    `about 200 lines` and `judged by the reviewer, not measured`.
  - In `tests/test_skills.py`: `test_description_fits_the_length_cap[name]`, every skill's
    description is at most 1024 characters (a pinning test from `apm:writing-skills`; it passes now
    and guards the appended sentences).
- [ ] **Step 2: Run** `python -m pytest -q tests/test_skills_clean_code.py tests/test_skills.py`.
  Expected: FAIL on the four trigger cases, the extract-method, references, type-check, passes-at-once
  and large-class tests; the length cap passes.
- [ ] **Step 3: Implement.** Append exactly these sentences to the descriptions:
  - `clean-code`: `Also use when the request mentions the boy scout rule, leaving code cleaner, continuous improvement, incremental quality improvements, improving naming, meaningful names, naming conventions, or unclear or misleading identifiers.`
  - `code-smells`: `Also use when the request mentions code smells, technical debt, reviewing code quality, or a systematic code quality assessment.`
  - `refactoring`: `Also use when the request is to break up a long function, reduce method length, decompose complex logic or simplify a function, or mentions complex branching, long if-else or switch-case chains, or applying Open-Closed to branching.`
  - `test-first`: `Also use when the request mentions TDD, test-driven development, writing tests first, test-first development, code that is testable by design, red-green-refactor, building features incrementally with tests, arrange-act-assert (AAA), given-when-then, organizing test code, or test readability.`

  Commit: `"Restore the original trigger phrases to the code skills' descriptions"`. Then the nuances:
  - `refactoring/SKILL.md:15`: the bullet becomes "A function is at or near the function limit
    (default 15 lines of logic; consider extracting from about 10 lines of logic), mixes levels of
    abstraction, or has a comment explaining what its next block does." Add the bullet
    "- Someone asks to simplify or decompose a function." to `## When this applies`
    (from `refactor-extract-method/SKILL.md:12,16`).
  - `refactoring/SKILL.md:83-84`: after "...whose name replaces the comment." insert "Short, focused
    functions with intention-revealing names make code read like prose." (`refactor-extract-method/SKILL.md:19`).
  - `refactoring/SKILL.md:160`: after "type checks or string comparisons on a kind" add
    "(examples by language in [references/examples-by-language.md](references/examples-by-language.md))";
    list the file in `## References`. The new file's row: generic "a type check before a call" →
    JavaScript, TypeScript, Java → `` `instanceof` `` (`refactor-replace-conditional-with-polymorphism/SKILL.md:40`).
  - `test-first/SKILL.md:95-96`: "If it passes immediately, it tests behavior that already exists:
    fix or delete it." becomes "If it passes immediately, it tests behavior that already exists: it
    is redundant, so delete it and pick a different behavior." (`tdd-red-green-refactor/references/cycle-steps.md:15`;
    our `cycle-steps.md:18` already says this and does not change).
  - `code-smells/SKILL.md:36`: the Large class rule gains "; or a single type of about 200 lines,
    even in a file under the file limit (judged by the reviewer, not measured)". At `:68-70` add one
    sentence after the first: "The one size signal it does not give is a single type of about 200
    lines in a file under the limit: that is judged by the reviewer, not measured."
  - `smell-catalog.md` `### Large class` **What:** gains the same clause as `:36`
    (`clean-code-detect-smells/SKILL.md:44`).
- [ ] **Step 4: Run** `python -m pytest -q tests/test_skills_clean_code.py tests/test_skills.py tests/test_coverage.py`.
  Expected: PASS. Then `<CLI> coverage` reports `Gaps: 0`.
- [ ] **Step 5: Commit** `"Restore the extract-method trigger and threshold, delete a test that passes at once, and add a class-size signal to the smells"`.

### Task 3: Design skills (solid, object-design, clean-architecture, functional-core)

**Files:**
- Modify: `skills/solid/SKILL.md` (description; `## Liskov substitution` signs at `:158-161`;
  `## Dependency inversion` signs at `:259-262`; `## References`)
- Modify: `skills/solid/references/srp-indicators.md` (`### In the structure`)
- Create: `skills/solid/references/examples-by-language.md`
- Modify: `skills/object-design/SKILL.md` (description; `## Common mistakes` string-form bullet at
  `:198`; `## References`)
- Modify: `skills/object-design/references/composition-patterns.md` (`## 3. Delegation`,
  `## 4. Mixins and traits`, `## When inheritance is still appropriate`)
- Create: `skills/object-design/references/examples-by-language.md`
- Modify: `skills/clean-architecture/SKILL.md` (description; `## Ports and adapters` signs at `:87`;
  `## References`)
- Modify: `skills/clean-architecture/references/port-adapter-anatomy.md` (`## Adapters`)
- Modify: `skills/clean-architecture/references/anti-corruption-layer.md` (`## Mapping strategies`,
  the extension-functions row)
- Create: `skills/clean-architecture/references/examples-by-language.md`
- Modify: `skills/functional-core/SKILL.md` (description; `## Pure functions` signs; `## Common
  mistakes` `:251`; `## References`)
- Modify: `skills/functional-core/references/purity-rules.md` (`## The two rules`,
  `## Immutable updates`)
- Create: `skills/functional-core/references/examples-by-language.md`
- Modify: `skills/CREDITS.md` (one sentence under helmedeiros/clean-code-skills)
- Test: `tests/test_skills_design.py`

**Interfaces:**
- Produces: `skills/solid/references/examples-by-language.md` with the table shape in Global
  Constraints (Task 9 adds a row to it); in `tests/test_skills_design.py`, `TRIGGERS`,
  `EXAMPLE_NAMES` and a `_names_term(text, term) -> bool` helper as in Task 2 (Tasks 8 and 9 add to
  this file after this task).

- [ ] **Step 1: Write the failing tests** in `tests/test_skills_design.py`:
  - `test_description_names_the_original_triggers[name]` (same shape as Task 2):
    - `solid`: `SRP`, `OCP`, `LSP`, `ISP`, `DIP`, `single responsibility`, `open-closed`,
      `Liskov substitution`, `interface segregation`, `dependency inversion`,
      `separation of concerns`, `multiple reasons to change`, `fat interfaces`,
      `depending on abstractions`, `decoupling`, `inheritance hierarchies`
    - `object-design`: `encapsulation`, `information hiding`, `exposing internal state`,
      `public fields`, `getter/setter abuse`, `invariants`, `composition over inheritance`,
      `fragile base class`, `combining behaviors`
    - `clean-architecture`: `ports and adapters`, `hexagonal architecture`,
      `clean architecture boundaries`, `separating infrastructure from the domain`,
      `domain isolation`, `anti-corruption layer`, `keeping the domain pure`,
      `infrastructure leakage`
    - `functional-core`: `pure functions`, `immutability`, `referential transparency`,
      `higher-order functions`, `HOFs`, `map, filter and reduce`, `callbacks`,
      `functional error handling`, `Result, Either or Option`, `Maybe monad`,
      `replacing try-catch with types`, `errors without exceptions`
  - Add `"examples-by-language.md"` to `REFERENCES` for all four skills.
  - `test_examples_by_language_keep_the_original_names[name]`, over `EXAMPLE_NAMES` (each a plain
    substring of the skill's new file):
    - `solid`: `` `instanceof` ``, `` `NotImplementedException` ``, `` `pg` ``, `` `mysql` ``,
      `` `axios` ``, `` `fs` ``, `PostgreSQL`, `MongoDB`
    - `object-design`: `` `toString()` ``, `` `ArrayList.get(index)` ``, `class extends Base`,
      `React class components`
    - `clean-architecture`: `` `express` ``, `` `pg` ``, `` `axios` ``, `Express`, `Fastify`,
      `Commander`, `yargs`, `RabbitMQ`, `Kafka`, `PostgreSQL`, `Stripe SDK`, `Nodemailer`,
      `Kotlin`, `C#`
    - `functional-core`: `` `{ ...obj, field: value }` ``, `` `[...items, newItem]` ``,
      `` `[...items].sort()` ``, `` `sort()` ``, `` `splice()` ``, `` `const` ``, `` `Date.now()` ``,
      `` `Math.random()` ``, `` `process.env` ``
  - `test_original_names_stay_in_the_by_language_files[name]`: for each skill, none of its
    distinctive names (`solid`: `instanceof`, `NotImplementedException`, `MongoDB`;
    `object-design`: `toString`, `ArrayList`; `clean-architecture`: `Fastify`, `Nodemailer`,
    `RabbitMQ`, `Stripe SDK`; `functional-core`: `Date.now`, `Math.random`, `process.env`) appears,
    by `_names_term`, in any `.md` under the skill whose name does not end in `-by-language.md`.
  - `test_generic_wording_points_at_its_examples[place]`, each place's text contains
    `examples-by-language.md`: `solid` SKILL `## Liskov substitution` and `## Dependency inversion`;
    `object-design` SKILL `## Common mistakes`; `composition-patterns.md` `## 3. Delegation`,
    `## 4. Mixins and traits` and `## When inheritance is still appropriate`; `clean-architecture`
    SKILL `## Ports and adapters`; `port-adapter-anatomy.md` `## Adapters`;
    `anti-corruption-layer.md` `## Mapping strategies`; `functional-core` SKILL `## Pure functions`;
    `purity-rules.md` `## The two rules` and `## Immutable updates`. (Use `section()` from
    `skill_helpers`.)
  - `test_hot_path_pitfall_names_performance_critical_paths`: the `functional-core` body contains
    `performance-critical hot path` and not `measured hot path immutable`.
  - `test_srp_indicators_carry_the_class_size_signal`: `### In the structure` of
    `srp-indicators.md` contains `about 200 lines` and `judged by the reviewer, not measured`.
  - `test_credits_say_where_the_original_names_are_kept`: `skills/CREDITS.md` contains
    `examples-by-language.md`.
- [ ] **Step 2: Run** `python -m pytest -q tests/test_skills_design.py`. Expected: FAIL (triggers,
  missing files, links, pitfall, signal, credits).
- [ ] **Step 3: Implement.** Append exactly these sentences to the descriptions:
  - `solid`: `Also use when the request mentions SRP, OCP, LSP, ISP or DIP, single responsibility, open-closed, Liskov substitution, interface segregation, dependency inversion, separation of concerns, multiple reasons to change, fat interfaces, depending on abstractions, decoupling, or inheritance hierarchies.`
  - `object-design`: `Also use when the request mentions encapsulation, information hiding, exposing internal state, public fields, getter/setter abuse, protecting invariants, composition over inheritance, the fragile base class, or combining behaviors.`
  - `clean-architecture`: `Also use when the request mentions ports and adapters, hexagonal architecture, clean architecture boundaries, separating infrastructure from the domain, domain isolation, an anti-corruption layer, keeping the domain pure, or infrastructure leakage.`
  - `functional-core`: `Also use when the request mentions pure functions, immutability, referential transparency, higher-order functions (HOFs), map, filter and reduce, callbacks, functional error handling, Result, Either or Option types, the Maybe monad, replacing try-catch with types, or handling errors without exceptions.`

  Commit: `"Restore the original trigger phrases to the design skills' descriptions"`. Then:
  - `functional-core/SKILL.md:251` becomes "**Making a performance-critical hot path immutable
    without measuring** the cost first." (`fp-pure-functions/SKILL.md:72`). Commit:
    `"Fix the self-contradicting hot-path pitfall"`.
  - `srp-indicators.md`: after the file-limit bullet (`:24`) add "- A single type of about 200 lines,
    even in a file under the file limit (judged by the reviewer, not measured)."
    (`solid-single-responsibility/references/srp-indicators.md:22`).
  - The four by-language files, from these originals (generic wording on the left):
    - `solid`: a type check before a call → `instanceof` (JavaScript, TypeScript, Java;
      `solid-liskov-substitution/SKILL.md:16,41`); a "not implemented" failure →
      `NotImplementedException` (C#; `:66`); infrastructure business logic imports → `pg`, `mysql`,
      `axios`, `fs` (JavaScript, TypeScript on Node.js; `solid-dependency-inversion/SKILL.md:39`);
      moving from one database to another → PostgreSQL to MongoDB (`:42`).
    - `object-design`: a string form that leaks structure → `toString()` (Java, JavaScript;
      `oop-encapsulation/SKILL.md:80`); a delegate's full surface → `ArrayList.get(index)` on a
      `Stack` (Java; `composition-patterns.md:52-63`); a mixin → the class-factory mixin, as a short
      code block (`const Serializable = (Base) => class extends Base {...}`, JavaScript; `:70-77`); a
      framework that requires inheritance → React class components (`:87`).
    - `clean-architecture`: infrastructure imports in the domain → `express`, `pg`, `axios`
      (JavaScript, TypeScript; `hexagonal-ports-adapters/SKILL.md:41`); adapter technologies → web
      framework: Express, Fastify; command-line parser: Commander, yargs; message broker: RabbitMQ,
      Kafka; relational database: PostgreSQL; payment provider's client library: Stripe SDK;
      mail-sending library: Nodemailer (`references/port-adapter-anatomy.md:48-60`); extension
      functions → Kotlin, C# (`hexagonal-domain-isolation/references/acl-patterns.md:104`).
    - `functional-core` (JavaScript, TypeScript; `fp-pure-functions/SKILL.md:30,40,73` and
      `references/purity-rules.md`): an immutable update → `{ ...obj, field: value }`,
      `[...items, newItem]`, `[...items].sort()` instead of `items.sort()`; operations that mutate in
      place → `sort()`, `splice()`; a binding that cannot be reassigned → `const`; the clock,
      randomness, the environment → `Date.now()`, `Math.random()`, `process.env`.
  - Each place named in `test_generic_wording_points_at_its_examples` gets one short pointer, for
    example "(examples by language: [examples-by-language.md](examples-by-language.md))", using
    `references/examples-by-language.md` from a `SKILL.md`. Each `SKILL.md` lists its file under
    `## References`.
  - `CREDITS.md`, after "Adapted, in the framework's own words and with language-neutral examples,
    into:" table, one sentence: "The library and language names the originals used as examples are
    kept in each skill's `references/examples-by-language.md`."
- [ ] **Step 4: Run** `python -m pytest -q tests/test_skills_design.py tests/test_skills.py tests/test_coverage.py`.
  Expected: PASS (the banned-term, link and spelling tests in `tests/test_skills.py` included). Then
  `<CLI> coverage` reports `Gaps: 0`.
- [ ] **Step 5: Commit** `"Keep the originals' library and language names as examples by language, and add the class-size signal to the SRP indicators"`.

### Task 4: branch-review

**Files:**
- Modify: `skills/branch-review/SKILL.md` (description; `### Module architecture` "Look for:" line)
- Test: `tests/test_skills_review.py`

**Interfaces:** none produced. Task 10 adds to `tests/test_skills_review.py` after this task.

- [ ] **Step 1: Write the failing tests** in `tests/test_skills_review.py`:
  - `test_branch_review_description_names_the_original_triggers`: the description contains, ignoring
    case, `branch review`, `code quality scorecard`, `compare code quality`.
  - `test_module_architecture_has_a_reviewer_judged_class_size_signal`: `### Module architecture`
    contains `about 200 lines` and `judged by the reviewer, not measured`.
- [ ] **Step 2: Run** `python -m pytest -q tests/test_skills_review.py`. Expected: FAIL (both).
- [ ] **Step 3: Implement.** Append to the description:
  `Also use when the request mentions a branch review or a code quality scorecard, or asks to compare code quality.`
  In `### Module architecture`, the "Look for:" sentence gains "any single type of about 200 lines,
  even in a file under the file limit (judged by the reviewer, not measured);" after "the largest
  files;". No rubric band changes.
- [ ] **Step 4: Run** `python -m pytest -q tests/test_skills_review.py tests/test_skills.py tests/test_coverage.py`.
  Expected: PASS.
- [ ] **Step 5: Commit** `"Restore branch-review's trigger phrases and add the class-size signal"`.

### Task 5: Retrieval check with the new descriptions (manager-run, no files change)

- [ ] **Step 1:** After Tasks 2 to 4 are merged, dispatch the same scenario as Task 1 with every
  description as it is on the branch.
- [ ] **Step 2:** Pass: all nine requests name the expected skill. Record the result under
  `## Retrieval check` beside the baseline. A miss is a finding for the task that owns that
  description: add the missing original wording to its sentence (within 1024 characters) and run the
  scenario again.

---

## Tasks that depend on the user's rulings (a to f)

Each of these is **dropped** unless the user rules for the option that needs it. The manager records
each ruling in italics here before the build starts.

*User's rulings at plan approval, 2026-10-24: A1, B1, C1, D1, E1 (keep ours), and F2 (add
`/apm:branch-review [branch]`). Tasks 6 to 10 are dropped; Task 11 is built.*

### Task 6 (ruling a): the full suite after each test

The originals run the full suite after each test (`tdd-test-first/SKILL.md:35`,
`references/test-first-checklist.md:24` "All existing tests still pass",
`tdd-red-green-refactor/references/cycle-steps.md:33`).
Ours runs targeted tests and the full suite once, through the gate: the user's own rule, recorded in
ADR-0001 and carried by `apm:executing-plans`, `apm:verification`, `apm:writing-plans` and the agents.
- **Option A1, keep ours:** Task 6 is dropped. Nothing changes.
- **Option A2, restore the original:** too large for this issue. ADR-0001 is superseded and five
  skills, the agent prompts and `tests/test_agents_workflow.py`, `tests/test_skills_workflow.py`
  change with it. Task 6 is dropped here and the manager files a separate issue for it.

### Task 7 (ruling b): a boy scout cleanup in the same commit

Original: "Keep it in the same commit or a separate commit" (`clean-code-boy-scout-rule/SKILL.md:35`).
Ours: refactoring and behavior never share a commit, no exception for small ones
(`clean-code/SKILL.md:141-144`, `refactoring/SKILL.md:64-66`, `references/improvement-checklist.md:35`).
- **Option B1, keep ours:** Task 7 is dropped.
- **Option B2, allow it:** after Task 2.
  - Files: `skills/clean-code/SKILL.md` (`## The boy scout rule`, step 5),
    `skills/refactoring/SKILL.md` (`## Refactor and behavior never share a commit`, last bullet;
    `## Common mistakes`, the "tiny rename" clause), `skills/clean-code/references/improvement-checklist.md`
    (`:35`), create `docs/adr/0011-boy-scout-cleanups-may-share-a-commit.md` and its row in
    `docs/adr/README.md`; test `tests/test_skills_clean_code.py`.
  - The rule text: "A boy scout cleanup of five minutes or less (a rename, an extraction, deleting dead
    code) in code the change already touches may go in the same commit as the behavior change, or in
    its own. Every other refactoring gets its own commit."
  - Failing tests first: `test_a_boy_scout_cleanup_may_share_the_behavior_commit`: `## The boy scout
    rule` contains `same commit`; `## Refactor and behavior never share a commit` contains
    `boy scout cleanup` and not `There is no exception for small changes`.
  - Run `python -m pytest -q tests/test_skills_clean_code.py tests/test_docs.py`. Commit
    `"Let a five-minute boy scout cleanup share the behavior commit (ADR 0011)"`.

### Task 8 (ruling c): the public-method threshold

Originals: SRP "More than 7 public methods" (`solid-single-responsibility/references/srp-indicators.md:23`),
smells "7+ public methods" (`clean-code-detect-smells/SKILL.md:44`). Ours, everywhere: 7 or more needs
a stated reason (the user's working agreement; `<CLI> metrics` flags 7 or more).
- **Option C1, keep ours:** Task 8 is dropped.
- **Option C2, restore "more than 7" in the SRP indicators only:** after Task 3. File
  `skills/solid/references/srp-indicators.md:25`: the bullet becomes "More than 7 public methods (the
  public-method limit, default 7, already asks a type with 7 for a stated reason: see
  `apm:object-design`)." Test `test_srp_indicators_say_more_than_seven_public_methods` in
  `tests/test_skills_design.py`. Run `python -m pytest -q tests/test_skills_design.py`. Commit
  `"Restore the SRP indicator's more-than-seven public methods"`. (Changing the flag `metrics`
  raises is out of scope per the issue.)

### Task 9 (ruling d): framework mocks in the examples

Originals: `jest.fn()` (`solid-dependency-inversion/references/dip-patterns.md:23`); `createMock`,
`toHaveBeenCalledWith`, `expect.stringContaining` (`tdd-arrange-act-assert/examples/aaa-patterns.md:57-76`).
Ours: hand-written recording fakes in pseudo-code.
- **Option D1, keep ours:** Task 9 is dropped.
- **Option D2, add the originals' mock forms as examples by language** (the pseudo-code keeps its
  fakes): after Tasks 2 and 3.
  - Files: create `skills/test-first/references/examples-by-language.md` (`createMock(EmailService)`,
    `toHaveBeenCalledWith`, `expect.stringContaining`, JavaScript with a mocking library), linked
    from `references/aaa-patterns.md` `## Pattern 4: an interaction` and from `test-first/SKILL.md`
    `## References`; add a row `` `jest.fn()` `` to `skills/solid/references/examples-by-language.md`,
    linked from `references/dip-patterns.md` section 1. Tests: `REFERENCES["test-first"]` and a
    names test in `tests/test_skills_clean_code.py`; `` `jest.fn()` `` added to
    `EXAMPLE_NAMES["solid"]` in `tests/test_skills_design.py`.
  - Run `python -m pytest -q tests/test_skills_clean_code.py tests/test_skills_design.py tests/test_skills.py`.
    Commit `"Keep the originals' mocking-library forms as examples by language"`.

### Task 10 (ruling e): the audit's long-method threshold

Original: "long methods ... more than 20 lines of logic" (`commands/clean-code-audit.md:25`). Ours: the
profile's function limit (default 15); `tests/test_skills_review.py:186` pins `"20 lines" not in body`.
- **Option E1, keep ours:** Task 10 is dropped.
- **Option E2, restore 20:** after Task 4. File `skills/clean-code-audit/SKILL.md` `### Refactoring`:
  "Long functions to extract: more than 20 lines of logic (the original audit's threshold). The
  profile's function limit still decides what is debt." This **replaces an existing assertion**:
  `test_audit_measures_against_the_profile_limits` drops `assert "20 lines" not in body`, and a new
  `test_audit_flags_functions_over_twenty_lines` asserts `more than 20 lines of logic` in
  `### Refactoring`. The ruling is the approval for that test change. Run
  `python -m pytest -q tests/test_skills_review.py`. Commit `"Restore the audit's 20-line long-method threshold"`.

### Task 11 (ruling f): a branch-review slash command

Original: the `branch-review` command took an optional branch argument (`commands/branch-review.md`,
Step 1). Ours: the skill already reviews "the branch you were given, otherwise the current branch";
there is no command, and the tutorial says `/apm:setup` is the only command the user types
(`docs/tutorial.md:20`).
- **Option F1, keep ours:** Task 11 is dropped.
- **Option F2, add `/apm:branch-review [branch]`:** no shared files; may run alongside anything.
  - Files: create `commands/branch-review.md` (frontmatter: a quoted `description`, and
    `argument-hint: "[branch]"`; body: the manager runs `apm:branch-review` on the branch in
    `$ARGUMENTS`, or the current branch when it is empty, through a reviewer as the skill says);
    modify `README.md` (where `/apm:setup` is listed) and `docs/tutorial.md:20` (name the optional
    command); test `tests/test_docs.py`.
  - Failing test first: `test_the_branch_review_command_takes_an_optional_branch`: the file exists,
    its frontmatter has a quoted description and `argument-hint`, and its body names `$ARGUMENTS` and
    `apm:branch-review`.
  - Run `python -m pytest -q tests/test_docs.py`. Commit `"Add /apm:branch-review with an optional branch"`.

---

### Task 12: The merge gate

- [ ] **Step 1: Run** `<CLI> gate 34`. Expected: the full suite passes once, and every criterion
  below holds. Then the PR, per `apm:finishing-a-branch`.

## Calls on the softened nuances (item 7 of the brief)

- **One assertion per test** (`tdd-red-green-refactor/references/cycle-steps.md:18` "Writing multiple
  assertions in one test (split them)" vs our `cycle-steps.md:21`): **left as ours.** The originals
  disagreed with each other: `tdd-arrange-act-assert/SKILL.md:30` allows several assertions of one
  behavior "from different angles". Ours ("about different behaviors") reconciles the two and matches
  our `test-first/SKILL.md:142-143`.
- **AAA "keep the setup minimal"** (`tdd-arrange-act-assert/SKILL.md:24`): **left as ours.** Our
  arrange step already says "the objects, data and dependencies this behavior needs, and nothing
  else" (`test-first/SKILL.md:139-140`), which is the original's "only what is relevant to this
  specific behavior". The long-arrange exception at `:186-187` covers a scenario that truly needs the
  setup, which the original also allows.
- **"Not every if-else needs a strategy pattern"** (`solid-open-closed/SKILL.md:66`): **left as ours.**
  `solid/SKILL.md:326` keeps it and makes it concrete ("Strategy objects for every if-else. Two stable
  branches are fine as they are."), and `refactoring/SKILL.md:190` adds "Not every conditional earns it."
- **branch-review's N/A for code with no user interface:** **left as ours.** It is not a softening:
  the originals had only the greenfield N/A (`commands/branch-review.md:104`). Ours added the no-UI
  N/A on purpose so a library or command-line project is not scored on styling or accessibility, and
  `tests/test_skills_review.py` pins it.

## Allowlisted actions

None. Every task creates or modifies files; nothing is deleted, no protected path is written, and no
destructive command runs. (Option B2 creates an ADR; option E2 changes one existing assertion, which
is a test edit, not a protected path, and is approved by that ruling.)

## Structural acceptance criteria (checked before the PR)

- Every changed description starts with `"Use when`, keeps its text on main word for word, ends with
  the one `Also use when` sentence this plan gives, and is at most 1024 characters
  (`tests/test_skills.py`).
- `skills/refactoring/`, `skills/solid/`, `skills/object-design/`, `skills/clean-architecture/` and
  `skills/functional-core/` each have `references/examples-by-language.md`, linked from their
  `SKILL.md`; no original library or language name appears in their other files (Tasks 2 and 3 tests;
  the banned-term test).
- The class-size signal appears in `code-smells/SKILL.md`, `code-smells/references/smell-catalog.md`,
  `solid/references/srp-indicators.md` and `branch-review/SKILL.md`; `<CLI> metrics` output and
  `standard.limits` are unchanged (no file under `scripts/` changes).
- No heading under `skills/` is renamed or removed; `<CLI> coverage` reports `Gaps: 0`.
- `test-first/SKILL.md` and `test-first/references/cycle-steps.md` agree: a test that passes at once
  is redundant and deleted.
- Every touched test file is at most 200 lines of logic and every function at most 15 (`<CLI> metrics`);
  `<CLI> debt check` passes; no existing test is weakened (the only assertion that may change is the
  one named in option E2, and only under that ruling).
- No file changes in `scripts/`, `hooks/`, `agents/`, `.apm/`, `tests/test_guard.py`, `tests/test_cli.py`,
  or the VirtualAirline repository; no version bump.
- If option B2 is ruled: `docs/adr/0011-boy-scout-cleanups-may-share-a-commit.md` exists and is listed
  in `docs/adr/README.md`.

## Retrieval check

*(Filled in by the manager in Tasks 1 and 5.)*

**Task 1 baseline, 2026-10-24, descriptions as on main (37785bf), one sonnet subagent, no tools:**

| # | Request | Expected | Chosen | Confidence |
|---|---|---|---|---|
| 1 | SRP, several reasons to change | solid | solid | high |
| 2 | composition over inheritance, fragile base class | object-design | object-design | medium (solid named as an alternative) |
| 3 | hexagonal architecture, ports and adapters | clean-architecture | clean-architecture | high |
| 4 | boy scout rule | clean-code | clean-code | medium (refactoring named as an alternative) |
| 5 | systematic assessment of technical debt | code-smells | **clean-code-audit** | medium (code-smells named as an alternative) |
| 6 | try-catch to a Result type | functional-core | functional-core | medium ("the description doesn't name Result types or exceptions") |
| 7 | break up a long function | refactoring | refactoring | medium (clean-code named as an alternative) |
| 8 | TDD, red-green-refactor | test-first | test-first | high |
| 9 | code quality scorecard for a branch | branch-review | branch-review | high |

One miss (5), five medium-confidence matches. Miss 5, verbatim: "A systematic assessment of technical
debt fits a whole-codebase audit that ranks findings, and its trigger names 'before planning a debt
paydown'. code-smells is a possible alternative."

**Task 5 check, 2026-10-24, descriptions as on the branch after Tasks 2, 3, 4 and 11 merged, one sonnet
subagent:** 9 of 9 chose the expected skill; 8 high confidence. Request 5 now chose code-smells
(medium: "clean-code-audit is a plausible rival because it audits a whole codebase and ranks findings,
but it never mentions technical debt in the description"). Every medium in the baseline (2, 4, 6, 7)
is now high. Pass.

## Final review

*Final review, 2026-10-24 (opus): 0 must-fix, 7 suggestions, ready to merge. Ruling by the manager,
re-grading by effect on a person using the result: S1 (duplicated test helpers, against Ruling 1's
intent), S2 (the tutorial contradicts itself about which commands you type), S3 (a regression test
that passes before the fix could be deleted under the restored Red rule), S4 ("the one size signal"
is false: parameter counts are not measured either), S5 (the new command does not tell the manager to
give the reviewer its brief, so the scorecard may lack `metrics` and `debt check`) and S7 (a test
fragile to re-wrapping, folded into S1) are fixed before merge, in one fix round. Cost if wrong: one
small fix round. S6 and the line-width note are deferred (below).*

## Deferred findings

- Final review S6: `skills/solid/references/examples-by-language.md` "not implemented" row has no
  pointer beside the ISP signs (`skills/solid/SKILL.md:211`).
- Final review, cosmetic: `skills/code-smells/SKILL.md:70` and `skills/branch-review/SKILL.md:146`
  are not reflowed to the files' usual width.
- Final review, recommendation: future retrieval runs should probe the neighbors directly ("audit the
  code quality of the whole codebase" → clean-code-audit; "apply the open-closed principle to this
  module" → solid; "review the code quality of this PR"), with several samples each.
- Final review, recommendation: original trigger words not in the issue's lists ("polymorphism",
  "replace conditionals", "refactor switch statements", "extending behavior without modifying code",
  "subtype behavior", "structure tests"); most are covered by existing wording. For the user.

## Pre-flight scan

| Pair or task | Shared file or interface | Found |
|---|---|---|
| Task 2 / Task 3 | Both define `_names_term(text, term) -> bool` in their own test file, and both duplicate `_term_pattern` in `tests/test_skills.py` | A duplicated block of logic, which the review rubric treats as a defect. Ruling 1 below. |
| Task 2 / Task 4 | none (disjoint skills and test files) | Clean. |
| Task 3 / Task 4 | none | Clean. |
| Task 11 / Tasks 2 to 4 | none (`commands/`, `README.md`, `docs/tutorial.md`, `tests/test_docs.py`) | Clean. |
| Task 2 / Task 5 | Task 5 checks Task 2's descriptions | Order only: Task 5 after 2, 3, 4 merge. |
| Task 2 self | Step 1 says the length-cap test "passes now"; Step 2 expects it to pass | Consistent (a pinning test). |
| Task 3 self | `EXAMPLE_NAMES["solid"]` has `` `fs` ``, a plain substring that also matches inside other names | Harmless: the test asserts presence only. |
| Task 4 self | Test asserts `branch review` in the description; the main description says "a scored quality review" | Consistent: the appended sentence adds "a branch review". |
| Task 11 self | Command file frontmatter; the tutorial says `/apm:setup` is the only command | Consistent: Task 11 changes the tutorial line. |
| Rubric check | Every test asserts something; no duplicated block except the row above | One finding (Ruling 1). |

*Ruling 1, pre-flight: Task 2 moves `_term_pattern` from `tests/test_skills.py` into
`tests/skill_helpers.py` as `term_pattern(term: str) -> re.Pattern[str]` (a pure move; the banned-term
test imports it), and adds `names_term(text: str, term: str) -> bool` there (case-insensitive search
with `term_pattern`). Task 2 owns `tests/skill_helpers.py`. Task 3 consumes `names_term` from
`skill_helpers` and defines no helper of its own, so Task 3 runs after Task 2 is merged. Order: Task 1,
Task 2, Task 4 and Task 11 first (at most three workers at once), then Task 3, then Task 5. Cost if
wrong: Task 3 waits for Task 2, about 15 minutes.*
