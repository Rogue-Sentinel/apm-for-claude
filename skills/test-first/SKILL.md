---
name: test-first
description: "Use when you are about to write a new behavior, a bug fix, a refactoring or any behavior change, before the first line of production code, and whenever you write, change, structure or review a test. Also use when the request mentions TDD, test-driven development, writing tests first, test-first development, code that is testable by design, red-green-refactor, building features incrementally with tests, arrange-act-assert (AAA), given-when-then, organizing test code, or test readability."
---

# Test first

Write the test. Watch it fail. Write the least code that makes it pass. Then clean up with the
tests green.

## When this applies

**Always**, for:
- a new feature or behavior;
- a bug fix;
- a refactoring (the tests that pin the behavior come first);
- any change in behavior;
- improving the testability of existing code (pin what it does with tests, then restructure);
- code that is being written, or already exists, without tests;
- writing, changing, structuring or reviewing a test, including its arrange-act-assert (or
  given-when-then) shape.

The only exceptions are throwaway prototypes, generated code and configuration files, and only the
user grants one: a worker asks the manager, and the manager asks the user. Thinking "skip it just
this once"? Stop. That is a rationalization (see below).

## The core rule

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

**If you did not watch the test fail, you do not know that it tests the right thing.** Breaking the
letter of this rule is breaking its spirit.

Wrote code before the test? Delete it and start over from the test. Do not keep it as a
"reference", do not "adapt" it while writing the tests, do not look at it. Delete means delete;
implement fresh from the tests.

The final test of any change: production code exists, a test for it exists, and that test was seen
failing first. Otherwise it was not built test-first, and no exception holds without the user's
permission.

## Test first

Writing the test first forces you to decide the behavior and the public interface before you commit
to an implementation. Code that is hard to test is usually hard to use, so test-first produces
better interfaces as a side effect.

1. **Define the behavior** in one plain sentence about an observable outcome: "What should the
   caller see happen?" Not how it is done.
2. **Write the test.** A name that states the behavior; the least context that matters (arrange);
   one call (act); one checked outcome (assert). No production code yet.
3. **Watch it fail, for the right reason**: the behavior is missing, not a typo or a bad import.
   If it fails for another reason, fix the test and run it again.
4. **Write just enough** production code to pass. Do not anticipate later requirements.
5. **Run the tests covering the change**: the test you wrote and the tests for the files you
   changed. Green: pick the next behavior. Anything red: fix it before moving on. The whole suite
   is not part of the cycle: it runs exactly once, through `<CLI> gate`, right before the pull
   request.

Test-after versus test-first:

```
Test after:  write register(email, password) with validation, hashing and saving;
             find it hard to test because it talks to the database;
             retrofit mocks; the tests come out fragile.

Test first:  test "registering with valid input returns a success result";
             this forces you to define "valid input" and "success result";
             the service naturally takes a repository interface, so the test can pass a fake;
             validation, hashing and saving each get their own test and emerge one at a time.
```

Before you start, while writing, after the failure and after the pass: work through
[references/test-first-checklist.md](references/test-first-checklist.md). It also lists which
behavior to test next (happy path, edge cases, error cases, boundaries).

## Red, green, refactor

The cycle is minutes long, not hours, and no phase is skipped: the discipline of the cycle is what
produces both correct and clean code.

```
RED       write one failing test for the next small behavior
  verify  it fails, and fails for the expected reason       -- wrong failure: back to RED
GREEN     the simplest code that passes
  verify  it passes, the covering tests pass, output clean  -- not green: back to GREEN
REFACTOR  improve the structure with everything green
  verify  still green after every step
NEXT      the next behavior, back to RED
```

- **Red.** One behavior, a clear name, real code (no mocks unless unavoidable). Run it. It must
  *fail*, not *error*, with the message you expected, because the feature is missing. If it passes
  immediately, it tests behavior that already exists: it is redundant, so delete it and pick a
  different behavior.
- **Green.** The least code that passes. Hard-coding a value is fine if it is the simplest path; the
  next test forces the generalization. Do not add options, features or "improvements" no test asks
  for, and do not refactor other code.

  ```
  GOOD  retryOperation(operation):
            for attempt in 1..3:
                try: return operation()
                on failure: if attempt == 3: fail with that failure
        -- just enough to pass "retries a failed operation three times"

  BAD   retryOperation(operation, options: { maxRetries, backoff: linear | exponential, onRetry })
        -- options no test asked for: you aren't going to need it
  ```
- **Verify green.** The test passes, the tests covering the files you changed still pass, and the
  output is clean (no new errors or warnings). "Covering tests" means the task's own tests **and the
  tests for every file you changed**, run with the project's own test command, even when your task
  named one test file: the task bounds what you deliver, not what you verify. The whole suite runs
  exactly once, through `<CLI> gate`, right before the pull request, and again only if the gate
  failed and something changed. A failure, including one you did not cause, goes in your report by
  name. A red test you saw scroll past and left out falsifies the report. Test failing? Fix the
  code, not the test.
- **Refactor**, only when green: remove duplication, improve names, extract helpers, simplify
  conditionals. One structural change at a time, tests after each. No new behavior. Refactoring
  commits are separate from behavior commits (`apm:refactoring`).

```
RED       test: calculator.add(2, 3) is 5          -- fails: add does not exist
GREEN     add(a, b): return 5                       -- simplest pass
RED       test: calculator.add(1, 1) is 2          -- fails, forces generalization
GREEN     add(a, b): return a + b
REFACTOR  rename, extract if it grows
```

The decision criteria, checklist and typical mistakes of each phase are in
[references/cycle-steps.md](references/cycle-steps.md).

## Arrange, act, assert

Every test tells a story in three acts, kept visibly apart. The same shape is also called
**given, when, then**: given the context, when the action happens, then the outcome holds.

1. **Arrange** the context: the objects, data and dependencies this behavior needs, and nothing
   else. Descriptive names that say why each value is there.
2. **Act** once: one call or trigger. Needing several calls usually means several behaviors.
3. **Assert** the outcome: one logical assertion. Several checks are fine only when they verify the
   same behavior from different angles.

Before, an unstructured test: setup, actions and checks interleaved, two behaviors in one, and a
name that says nothing:

```
test "user":
    db.insert(name: "Alice", role: "admin")
    u = service.getUser("Alice")
    expect(u).toExist()
    expect(u.role).toBe("admin")
    service.promote(u)
    expect(u.role).toBe("superadmin")
```

After, two tests, each with one behavior and visible phases:

```
test "getUser returns the user with their assigned role":
    // arrange
    db.insert(name: "Alice", role: "admin")

    // act
    user = service.getUser("Alice")

    // assert
    expect(user.role).toBe("admin")

test "promote raises an admin to superadmin":
    // arrange
    user = createUser(role: "admin")

    // act
    service.promote(user)

    // assert
    expect(user.role).toBe("superadmin")
```

Signs it is missing: no visible separation between setup, action and checks; assertions scattered
through the body; several actions before the first assertion; setup copied into many tests
(extract a helper or a shared setup); a name that does not describe the scenario. When testing
for an error, act and assert may merge into one line; that is the one accepted deviation. A long
arrange step is legitimate when the scenario truly needs it (a scripted end-to-end run, say), as
long as act and assert stay single and clear.

More patterns (value, state change, error, interaction, table-driven) and anti-patterns are in
[references/aaa-patterns.md](references/aaa-patterns.md).

## A bug fix starts with a failing test

**Reproduce the bug as a failing test before touching the fix.** The test must fail on the current
code, proving it captures the real defect; only then make it pass. A bug fix without a regression
test is not done.

```
bug:      an empty email address is accepted

RED       test "rejects an empty email":
              result = submitForm(email: "")
              expect(result.error).toBe("Email required")
verify    FAIL: expected "Email required", got nothing
GREEN     submitForm(data): if data.email is blank: return error "Email required"
verify    PASS, covering tests green
REFACTOR  extract validation if more fields need it
```

The test proves the fix, and stays to stop the bug coming back. Never fix a bug without one. For
finding the root cause first, use `apm:systematic-debugging`.

## No test skips

**Every test runs on every run of the suite.** No skip markers, no environment-variable gates, no
hidden or tagged-off tests, no "run only if the tool is installed". A test that skips proves nothing
and rots silently while looking green.

If a test needs an external resource, either commit the resource with the tests and treat its
absence as a **failure**, or have the test generate an equivalent itself. A check against a real
installation, device or service is a manual verification step that is run and reported, never a
conditional test.

## No test waits on a person

**No test, and no test run, may wait for a person.** A failed assertion, a debug assertion or a crash
must fail the test, never open a dialog, a prompt or a debugger. The test harness disables every
interactive prompt and dialog, and every new test target uses that same setup. A test never reads
from an interactive input, never sleeps waiting for someone, and never needs a manual step to
finish. Guard against crashes that would hang a run: never index a collection a test has not
checked is non-empty.

## Never weaken a test

**Never delete, skip or weaken a test to get a green build.** Weakening includes loosening an
assertion, widening a tolerance, catching the error the test expects to see raised, marking it
expected-to-fail, or editing the expected value to match what the code now does.

If a test is genuinely wrong, fix it deliberately, as its own visible change, and say so out loud in
the commit and the report: what was wrong with it, and why the new version is right. A test that
fails is information; report red as red.

## Writing good tests

Two principles govern every test:

1. **Every test names the break it catches.** Before writing the body, name the production change
   that would make it fail, and check that change is a bug rather than a decision. Derive expected
   values by hand (literals, hand-checked fixtures); an expectation computed by the code under test
   passes whatever that code does. No change detectors: test the behavior that depends on a
   constant or a wording, not the constant itself. Test your code's contract at its boundary, not
   the framework's mechanics.
2. **Every test exercises the real thing.** A mock earns no assertions; assert the real component's
   behavior. Mock only the slow or external level, after learning every side effect of what you
   replace. Make doubles specific, mirror real data completely, keep test-only code out of
   production types, and switch to real components when mock setup outgrows the test.

| Quality | Good | Bad |
|---------|------|-----|
| Minimal | one thing; "and" in the name means split it | `test "validates email and domain and whitespace"` |
| Clear | the name describes the behavior | `test "test1"` |
| Shows intent | demonstrates the wanted interface | obscures what the code should do |

```
GOOD  test "retries a failed operation three times":
          attempts = 0
          operation = function(): attempts += 1; if attempts < 3: fail "boom"; return "success"
          result = retryOperation(operation)
          expect(result).toBe("success")
          expect(attempts).toBe(3)
      -- clear name, real behavior, one thing

BAD   test "retry works":
          mock = fakeThatFailsTwiceThenSucceeds()
          retryOperation(mock)
          expect(mock.callCount).toBe(3)
      -- vague name, tests the mock rather than the code
```

Before finishing a test file, run the mutation check: mentally break the code (wrong constant,
wrong branch, missing side effect, empty return, missing validation) and confirm a test fails for
each. The full rules, gate checks, quick reference and warning signs are in
[references/writing-good-tests.md](references/writing-good-tests.md). Load it whenever you write or
change a test.

## Rationalizations

| Excuse | Reality |
|--------|---------|
| "Too simple to test." | Simple code breaks. The test takes thirty seconds. |
| "I'll test after." | A test written after passes at once, which proves nothing. It may test the wrong thing, test the implementation instead of the behavior, or miss the case you forgot. You never saw it fail, so you never proved it can catch the bug. |
| "Tests after achieve the same goal; it's the spirit, not the ritual." | Tests after answer "what does this do?"; tests first answer "what should this do?" Tests after are biased by the code: you verify the cases you remembered, not the ones you would have discovered. |
| "I already tested it by hand." | Manual testing leaves no record, cannot be re-run when the code changes, and forgets cases under pressure. "It worked when I tried it" is not coverage. |
| "Deleting hours of work is wasteful." | Sunk cost. The time is spent either way. The real choice is rewrite with tests first (high confidence) or bolt tests on (low confidence). Keeping code you cannot trust is the waste. |
| "I'll keep it as a reference and write the tests first." | You will adapt it, and that is testing after. Delete means delete. |
| "I need to explore first." | Fine. Throw the exploration away, then start from a test. |
| "It's hard to test, so the design must be unclear." | Listen to the test: hard to test means hard to use. Simplify the design. |
| "This will slow me down." | Test-first is the fast path: bugs caught before commit, no regressions, refactoring without fear. Shortcuts mean debugging later, which is slower. |
| "Manual testing is faster." | It does not prove edge cases, and you redo it on every change. |
| "The existing code has no tests." | You are improving it. Add tests for the code you touch. |

## Red flags

Any of these means: delete the code, start over from a test.

- Code before the test, or a test written after the implementation.
- A new test that passes immediately.
- You cannot explain why the test failed.
- Tests planned for "later".
- "Just this once", "this case is different because...".
- "I already tested it by hand."
- "Tests after achieve the same purpose", "it's about the spirit, not the ritual".
- "Keep it as a reference", "adapt the existing code".
- "I already spent hours on it; deleting is wasteful."
- "Test-first is dogmatic; I'm being pragmatic."

## When stuck

| Problem | What to do |
|---------|-----------|
| You do not know how to test it | Write the interface you wish you had; write the assertion first; ask (a worker asks the manager). |
| The test is too complicated | The design is too complicated. Simplify the interface. |
| Everything has to be mocked | The code is too coupled. Pass dependencies in. |
| The setup is huge | Extract setup helpers. Still huge? Simplify the design. |

## References

- [references/cycle-steps.md](references/cycle-steps.md): each phase of the cycle, with decision
  criteria, checklists and mistakes.
- [references/test-first-checklist.md](references/test-first-checklist.md): the checklist before,
  during and after, what to test next, and the completion checklist.
- [references/aaa-patterns.md](references/aaa-patterns.md): arrange-act-assert patterns and
  anti-patterns.
- [references/writing-good-tests.md](references/writing-good-tests.md): naming the break, exercising
  the real thing, mocks, the mutation check and warning signs.

## Common mistakes

- **Writing the test and the code in one mental step.** Slow down: the test is written, run and seen
  failing before any code.
- **Skipping the failure step.** You must see it fail.
- **Too much code in green**, or the "real" algorithm before a test demands it; error handling no
  test asked for.
- **Skipping refactor** under time pressure, or **refactoring while red**.
- **Tests that are too big**, covering several behaviors at once; several actions in one test.
- **Testing private functions directly** instead of through the public interface; asserting
  implementation details instead of outcomes.
- **Integration tests where a unit test suffices** for the current behavior.
- **Designing the whole architecture before the first test.**
- **Arranging more than the behavior needs**, or relying on hidden global state with no arrange.
- **Vague test names** that do not describe the scenario.
- **Running only your own test file** and calling the change verified, when other files' tests cover
  what you touched.
- **Getting stuck on what to test next.** Pick the simplest next behavior; when unsure, the happy path.
