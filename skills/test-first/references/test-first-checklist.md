# Test-first checklist

Use this before writing any production code.

## Before you start
- [ ] Can you describe the behavior you want in one sentence?
- [ ] Is this the smallest increment you can test?
- [ ] Do you know the expected output or side effect?
- [ ] Can you name the production change that would make the test fail, and is it a bug rather
      than a decision?

## Writing the test
- [ ] The name describes a behavior, not a function name.
- [ ] The test has a single reason to fail.
- [ ] It uses the public interface, not internal functions.
- [ ] It does not depend on the order tests run in.
- [ ] It needs no complex setup. If it does, the design may need simplifying.
- [ ] The expected value is derived by hand, not by the code under test.
- [ ] It cannot skip, and it cannot wait on a person.

## After the test fails
- [ ] The failure message clearly says what is missing.
- [ ] The failure is not a typo or an import error.
- [ ] You know exactly what production code is needed.

## After the test passes
- [ ] You wrote the least code that passes.
- [ ] The whole suite still passes, run with the project's own test command.
- [ ] The output is clean: no new errors or warnings.
- [ ] The code is ready to refactor, if it needs it.

## What to test next

Work through these, picking the next simplest behavior. When you cannot decide, start with the
happy path.

1. **Happy path:** the most common successful case.
2. **Edge cases:** empty input, zero, nothing, a single element, the maximum.
3. **Error cases:** invalid input, a missing dependency, a timeout.
4. **Boundaries:** off-by-one, limits, transitions between states.

## Before you call it done

- [ ] Every new function or method has a test.
- [ ] You watched each test fail before implementing it.
- [ ] Each failed for the expected reason (the feature was missing, not a typo).
- [ ] You wrote the least code to pass each one.
- [ ] Every test passes.
- [ ] The output is clean.
- [ ] Tests use real code; mocks only where unavoidable.
- [ ] Edge cases and errors are covered.

Cannot tick every box? Test-first was skipped. Start over from a test.

## Signs you are doing it right
- Each test adds one new assertion about behavior.
- Production code grows in small, confident steps.
- You rarely write code no failing test demanded.
- Refactoring feels safe, because the suite catches regressions.
- The public interface emerges from what the tests need.

## Signs you are not
- Production code exists with no test for it.
- Tests were added after the code was "done".
- Tests mirror the implementation's structure instead of describing behavior.
- A whole type was written before its first test.
- Mocking is heavy because the code was not designed to be tested.
