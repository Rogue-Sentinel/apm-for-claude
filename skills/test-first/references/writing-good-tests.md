# Writing good tests

**Load this when** you write or change a test, add a mock or other double, or add a cleanup or
helper function for tests.

A test exists to catch a specific break. Two principles govern everything here:

```
1. Every test names the break it catches.
2. Every test exercises the real thing.
```

Strict test-first produces both naturally: a test written first and watched failing against real
code has already proven it can fail, and it only earns a double when the real dependency proves slow
or external.

## Principle 1: name the break

Before writing the body, answer: **which production change should make this test fail, and is that
change a bug or a decision?** A test earns its place by catching a wrong branch, a missing side
effect, a wrong argument, a boundary case or a broken contract.

**Derive expectations independently.** Use literals and hand-checked fixtures; a table of cases with
literal expected values is the preferred shape. An expected value computed by the code under test,
or by its helpers, passes whatever that code does:

```
// BAD: a mirror assertion; the same builder computes both sides, so it is always true
expected = buildSearchQuery(tag: "urgent")
expect(buildSearchQuery(tag: "urgent")).toBe(expected)

// GOOD: a hand-derived literal
expect(buildSearchQuery(tag: "urgent")).toBe('tag:"urgent"')
```

**No change detectors.** If only intentional decisions can fail a test (a constant's value, the
exact wording of a message, private structure), it fires on every redesign and sleeps through bugs.
Test the behavior that depends on the decision: not "`MAX_RETRIES` is 5" but "a failing call is
retried 5 times and a sixth attempt never happens".

**Behavior, not text.** Asserting that a script or configuration file contains an exact line proves
only that the source is the source. Run the script against controlled inputs and assert its outputs,
side effects or exit codes. Documents that instruct agents are proven by the behavior of the agent
that reads them (see `apm:writing-skills`); a structural check that a required section exists is a
different thing, a contract other tools anchor to. Prose meant only for people earns no test.

**Your code, not the framework.** Test the contract your code makes at its boundaries: the route you
register, the query you emit, the payload you produce. Upstream mechanics are their maintainers'
tests to write. The classic mistake is asserting that the router calls a registered handler: that is
the router's test, not yours. When upstream behavior genuinely surprised you, write one narrow
characterization test that names the assumption. The same boundary holds inside your own code:
constructors, accessors, constants and plain forwarding earn tests only when they validate,
normalize, default, derive, enforce or cause side effects. Otherwise, assert the first result a
consumer can see that depends on them.

### Gate: before writing the test body

```
Name the production change that would make this test fail.

  cannot name one              -> redesign around an observable behavior
  "the source text changed"    -> run the artifact and assert its effects
  only intentional decisions   -> a change detector; test the behavior that depends on the decision

Confirm the expected value is derived without the code under test.
  it reuses the code's logic or helpers -> replace it with a literal or a hand-checked fixture
```

## Principle 2: exercise the real thing

**The mock earns no assertions.** An assertion about a mock passes when the mock is present and
fails when it is absent; it says nothing about the component. Assert the real component's behavior.
If the mock is what you are checking, unmock it or delete the assertion.

```
// GOOD: real behavior
expect(page.findByRole("navigation")).toExist()

// BAD: the mock's existence
expect(page.findByTestId("sidebar-mock")).toExist()
```

The question to ask yourself: "Am I testing the behavior of a mock?"

**Mock at the right level.** Learn every side effect of the real function before replacing it. Mock
the slow or external operation, and keep real everything the test depends on. When unsure, run the
test against the real implementation first and watch what actually has to happen.

```
// BAD: the mock swallows the configuration write that duplicate detection reads
replace toolCatalog.discoverAndCacheTools with a stub that does nothing

// GOOD: replace only the slow server start-up; the configuration write stays real
replace serverManager.start with a stub
```

**Make doubles specific.** When arguments, call counts or ordering are part of the contract, assert
them; a fake that accepts anything verifies nothing. Give each branch (success, error, malformed) its
own fixture or recording double, so the wrong branch cannot satisfy the expectation.

**Mirror real data completely.** A fake response carries the complete structure as it exists in
reality, every documented field, not only the ones this test reads. A partial fake fails silently
when downstream code reads an omitted field: the test passes while the integration breaks.

**Production types carry production methods only.** Cleanup that only tests need lives in test
utilities, never as a `destroy()` on the production type. Ask: is this method called only from
tests? Does this type own this resource's lifecycle? A wrong answer to either means a test utility.

**Prefer real components to complex mocks.** When mock setup outgrows the test logic, mocks miss
methods the real components have, or tests break whenever a mock changes, switch to an integration
test with the real components. The question to ask: "Do we need a mock here at all?"

### Gate: before adding a mock or test helper

```
List the real function's side effects; keep the ones the test depends on real,
and mock the slow or external level below them.

Fake responses mirror the complete real structure.

A function only tests call lives in test utilities, not in production code.

About to assert on the mock itself?
  -> unmock it, or delete the assertion
```

## Tests ship with the implementation

Failing test, minimal implementation, refactor: that cycle is what "complete" means. Ship the tests
the behavior needs, and only those. Trivial code and prose for people earn none, and a test written
only to satisfy a process costs maintenance forever.

## The mutation check

Before finishing, mentally mutate the production code. At least one test should fail for each
realistic mutation:

- a wrong constant or argument;
- the wrong branch's handler;
- a missing change of state or side effect;
- an empty or default return;
- missing validation for zero, empty, nothing, unauthorized or malformed input.

A mutation nothing catches marks the behavior as unprotected, or the test as tautological.

## Quick reference

| When you... | Do |
|-------------|----|
| write any test | name the break it catches: a bug, not a decision |
| build an expected value | derive it by hand, never with the code under test |
| test a script or a document | run it, or test its consumer; never grep its text for behavior |
| reach for a dependency's behavior | test your boundary contract, not its documented mechanics |
| want to assert on a mocked element | test the real component, or unmock it |
| are about to mock a function | learn its side effects; mock the slow or external level |
| build a fake response | mirror the real structure completely |
| need cleanup only tests use | put it in test utilities |
| watch mock setup balloon | switch to an integration test with real components |
| finish a test file | run the mutation check |

## Warning signs

- Setup and assertion share the same object, so equality is guaranteed.
- The test can only fail through a crash, a panic or a missing element.
- It fails on every intentional change and never on an accidental break.
- Expected values hide behind loops, builders or helpers.
- It greps source text, or asserts that a removed symbol stays removed.
- It would still matter if only the framework remained.
- It exists for coverage, checking no outcome or side effect.
- An assertion checks a mock's test identifier, or fails if you remove the mock.
- A method is called only from test files.
- Mock setup is more than half the test, or you cannot say why the mock is needed.
- Mocking "just to be safe".
