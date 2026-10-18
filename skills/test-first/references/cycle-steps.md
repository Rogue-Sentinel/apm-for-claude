# Red, green, refactor: the steps

## Phase 1: red, a failing test

### Decide
- What is the simplest next behavior the system should show?
- Can it be expressed in a single assertion?
- Does this test add information no existing test already covers?

### Do
1. Name the test after the behavior, not the function: `calculates the total with a discount`, not
   `test calculate`.
2. Write the assertion first, then work backward to the setup it needs.
3. Run the test. It must fail.
4. Read the failure message. It should say exactly what is missing: a type, a function, a return
   value. A failure that is an error (a typo, a bad import, a crash in setup) is not the red you
   want: fix it and run again.
5. If the test passes immediately, it is redundant: delete it and pick a different behavior.

### Mistakes
- Several assertions about different behaviors in one test: split them.
- Describing the implementation instead of the behavior.
- Skipping the run. You must see it fail.

---

## Phase 2: green, make it pass

### Decide
- What is the absolute least code that makes this test pass?
- Am I writing anything no test demands?

### Do
1. Write only enough code to pass the failing test.
2. Hard-coding, constants and duplication are all acceptable here; the next test or the refactor
   phase removes them.
3. Run the tests covering the change: the one you wrote and the tests for the files you changed,
   with the project's own test command. Everything must be green, and the output clean. The whole
   suite is not part of the cycle: it runs once, through `<CLI> gate`, right before the pull request.
4. If a test that used to pass now fails, fix that before anything else. Fix the code, not the test.

### Mistakes
- Implementing the "real" algorithm too early.
- Adding error handling before a test demands it.
- Refactoring during green. Wait for the refactor phase.

---

## Phase 3: refactor, improve the design

### Decide
- Is there duplication to remove?
- Are the names clear and in the domain's language?
- Are there long functions to extract?
- Can a conditional be simplified?

### Do
1. Start only with every test green.
2. Make one structural change at a time.
3. Run the tests after each change.
4. Stop when the code clearly says what it does.
5. Add no new behavior. Commit the refactoring separately from behavior.

### Moves
- **Remove duplication:** extract the shared logic into a function or a variable.
- **Rename:** make names match the domain language.
- **Extract method:** break long functions into focused, named steps.
- **Inline:** remove indirection that adds nothing.
- **Simplify conditionals:** replace nested conditions with guard clauses, or with polymorphism.

### Mistakes
- New features disguised as refactoring.
- Refactoring without running the tests between changes.
- Over-engineering: extracting abstractions before a second use exists.

---

## Repeat

Pick the next small behavior and go back to red. The tests drive the design forward one assertion at
a time; each cycle takes minutes.

Signs the cycle is not being followed: production code written before any test; large batches of
code between test runs; tests that pass on their first run; refactoring skipped because "it works";
tests that check implementation details instead of behavior.
