---
name: functional-core
description: "Use when code holds state, has side effects, reads the clock, randomness or the environment, signals absence or failure, or repeats a loop that differs in one operation, so the decisions become pure functions over values and the effects move to the edges. Also use when the request mentions pure functions, immutability, referential transparency, higher-order functions (HOFs), map, filter and reduce, callbacks, functional error handling, Result, Either or Option types, the Maybe monad, replacing try-catch with types, or handling errors without exceptions."
---

# A functional core

Decisions are pure functions over plain values. Effects (input and output, the clock, randomness,
mutation) happen in a thin shell around them. Absence and failure are values the caller can see.

## When this applies

- A function changes something outside itself: a global, a field, a database, a file, the network.
- A function gives different results for the same inputs, or its result depends on when, or how
  often, it is called.
- A function reads the current time, a random number, an environment variable or a global setting.
- A test needs elaborate setup or mocks because of hidden dependencies, or a bug is hard to find
  because state changes are scattered.
- Several loops share their structure and differ only in the operation applied, or you are writing
  collection-processing boilerplate, an event handler, a middleware chain or a plugin hook.
- A function signals "nothing" or "failed" with a sentinel (`0`, `-1`, an empty string, a null),
  a boolean success flag, or an exception used for ordinary control flow.
- Error handling is scattered, inconsistent or forgotten: some callers catch, others do not, and
  try-catch blocks nest.
- Someone names an idea from this skill (pure functions, side effects, immutability, referential
  transparency, higher-order functions, map, filter and reduce, callbacks, result, either, option or
  maybe types, functional error handling) and you need to apply it.

## The core rule

**Keep the core pure and push the effects to the edges.** The logic that decides things takes
values and returns values: the same inputs always give the same output, and it changes nothing.
The shell around it gathers the inputs (reads the database, the clock, the request), calls the
core, and carries out what the core returned. Absence and failure are part of the return type, not
a sentinel and not an exception. Time and randomness come in as parameters.

The payoff is testing: a pure core is tested with nothing but inputs and expected outputs, no
mocks, in milliseconds. This is the same rule as `apm:clean-architecture`, seen from inside one
function.

## Pure functions

A pure function has two properties: **given the same inputs it always returns the same output, and
it has no side effects.** Combine it with **immutable data** (values that cannot change after they
are made) and a program becomes easy to reason about, test and run in parallel. Side effects are
not eliminated; they are moved to the boundary.

1. **Find the impurities**: reads or writes of outside state (globals, fields, the database, files,
   the network), the current time, random numbers.
2. **Separate the pure logic from the effects.** Extract the computation into its own function. The
   impure function becomes a thin shell that gathers inputs, calls the pure function, and applies
   its outputs.
3. **Make the data immutable.** Build a new value instead of changing an old one; prefer bindings
   that cannot be reassigned; return new collections instead of modifying the ones you were given.
4. **Pass dependencies as arguments.** A hidden dependency (global configuration, a singleton, the
   current time) becomes an explicit parameter that the caller supplies.
5. **Verify purity.** A function is pure when you can replace any call to it with its return value
   and nothing changes (referential transparency). Its tests need only inputs and expected outputs,
   no mocks.

Signs: a function that reads or writes a global; a call to the clock, a random source or the
environment; a function that modifies its parameters; a result that changes with when or how
often it runs; tests that have to mock side effects; a variable reassigned all through a function.

Before:

```
total = 0                                  // shared, mutable

function addToTotal(amount):
    total = total + amount                 // changes outside state
    log("Total: " + total)                 // a side effect
    return total
```

After:

```
function addAmount(currentTotal, amount):  // pure: a new value, no mutation
    return currentTotal + amount

// the shell, at the boundary
total = addAmount(total, amount)
log("Total: " + total)
```

The two rules in detail, the list of side effects, the purity test, immutable updates of objects,
lists and nested values, the pure-core-and-impure-shell pattern and the table of pure alternatives
are in [references/purity-rules.md](references/purity-rules.md).

## Higher-order functions

A higher-order function takes a function as an argument or returns one. It captures a common
pattern (iterate, transform, filter, accumulate, compose) and takes the varying part as a
parameter, which removes structural duplication and gives small, reusable building blocks.

1. **Find the pattern**: two or more blocks with the same structure that differ in one operation.
   The shared structure is the higher-order function; the varying operation is its argument.
2. **Extract the higher-order function** that takes the varying behavior as a parameter, and
   replace the duplicated blocks with calls to it.
3. **Use the built-in ones first.** Most languages provide map, filter, reduce (fold), for-each,
   flat-map, find, any and all. Use them instead of hand-written loops, and do not write your own
   where one exists.
4. **Compose them into a pipeline.** Each step does one thing, and the chain reads as a
   description of the transformation.
5. **Check readability.** If the chain is hard to read, name the intermediate steps, as variables
   or as named functions. The goal is clarity, not cleverness.

Signs: a loop that transforms, filters or accumulates; several functions identical but for one
operation; a callback pattern that could be generalized; manual iteration where a declarative
pipeline would be clearer; closures built over configuration.

Before:

```
emails = []
for user in users:
    if user.active:
        emails.append(user.email)
```

After:

```
emails = users
    .filter(user -> user.active)
    .map(user -> user.email)
```

Transform, filter, accumulate, function factories, composition, middleware pipelines and partial
application, with the chaining dos and don'ts, are in
[references/hof-patterns.md](references/hof-patterns.md).

## Absence and failure are values

**Absence is a typed value, never a sentinel.** Not `0`, not `-1`, not an empty string, not a bare
null that every caller must remember to check: the language's optional type, or an option type.
**An expected failure is a typed value too**: a result that is either a success with its value or a
failure with its reason. Exceptions are invisible in a function's signature and easy to forget; a
return type makes the failure part of the contract, and the caller has to handle it.

1. **Find the candidates**: functions that throw for expected outcomes, return a null or a sentinel
   for "not found" or "failed", or return a boolean success flag.
2. **Choose the type.**
   - An **option** (maybe): the value may or may not exist, and no reason is needed.
   - A **result** (either): the operation may succeed with a value or fail with an error value
     that says why.
3. **Return it instead of throwing.** The signature changes from returning a value (and sometimes
   throwing) to returning a result of value or error. The caller matches on it or chains on it.
4. **Compose the fallible steps** with map (transform the success), flat-map (chain another
   fallible step) and map-error (transform the failure). Each step works on the success value, and
   the first failure carries through to the end.
5. **Handle it at the boundary.** Turn the typed error into a response, a message, an exit code or
   (where the platform demands one) an exception at the edge of the system: the request handler,
   the entry point. The domain stays pure.

Signs: try-catch used for business flow; a null meaning "not found" or "failed"; `if not
save(data): ...`; some callers catching and others not; deeply nested try-catch; an exception
caught and immediately rethrown, or logged and swallowed.

Before:

```
function parseAge(input):
    age = toInteger(input)
    if age is not a number: fail "invalid age"
    if age < 0: fail "age cannot be negative"
    return age

// the caller has to remember to catch
try:
    save(parseAge(input))
catch error:
    showError(error.message)
```

After:

```
function parseAge(input) -> Result of (number, text):
    age = toInteger(input)
    if age is not a number: return Err("invalid age")
    if age < 0: return Err("age cannot be negative")
    return Ok(age)

// the caller cannot ignore either case
parseAge(input)
    .map(age -> save(age))
    .mapErr(message -> showError(message))
```

A truly exceptional, unrecoverable condition (a broken invariant, the machine running out of
memory) may still be an exception; a missing record or a bad input is not. The option and result
operations, a chained example, the decision guide and the anti-patterns are in
[references/result-and-option.md](references/result-and-option.md); what each language provides is
in [references/result-and-option-by-language.md](references/result-and-option-by-language.md).

## Time and randomness are parameters

**The clock is a parameter.** Logic that depends on the time takes the time (or a clock to ask) as
an input, so a test can set it. The same holds for every other source of non-determinism: random
numbers, generated identifiers, the environment, configuration read from outside.

- **Pass the value when you can**: `isExpired(token, now)` rather than `isExpired(token)` that
  reads the clock inside. The caller at the edge reads the clock once and passes it in.
- **Pass a port when the logic needs to ask more than once**: a `Clock` (with `now()`) or a
  `RandomSource` (with `next()`) interface, implemented by the system clock in production and by a
  fixed or scripted one in tests. See `apm:clean-architecture`.
- **Pass a seed or the drawn values** for randomness, so a test can replay the same sequence.
- **Read the environment and configuration at the edge**, once, into a value that the core
  receives as a parameter.
- **A scripted sequence makes a whole scenario a unit test.** When the core takes its inputs one
  sample at a time (a reading, an event, a tick), a test can feed a scripted sequence, and a long
  real-world process becomes a deterministic test that runs in milliseconds.

Before:

```
function isTrialOver(account):
    return clock.systemNow() - account.startedAt > 30 days   // a test cannot control this
```

After:

```
function isTrialOver(account, now):
    return now - account.startedAt > 30 days

// a test
assert isTrialOver(account(startedAt: day 0), now: day 31) == true
assert isTrialOver(account(startedAt: day 0), now: day 30) == false
```

## References

- [references/purity-rules.md](references/purity-rules.md): the two rules, side effects, the
  purity test, immutable updates, the pure core and impure shell, and pure alternatives.
- [references/hof-patterns.md](references/hof-patterns.md): seven higher-order function patterns
  and how to chain them readably.
- [references/result-and-option.md](references/result-and-option.md): option and result, their
  operations, when to use which, and the anti-patterns.
- [references/result-and-option-by-language.md](references/result-and-option-by-language.md): what
  each language offers for absence and failure.

## Common mistakes

- **Reading "no side effects" as "no input or output anywhere."** The effects move to the
  boundary; they do not disappear.
- **Deep-copying nested values needlessly.** Share the unchanged parts (structural sharing), or use
  an immutable collection.
- **Making a measured hot path immutable without measuring** the cost first.
- **Forgetting which operations mutate in place**: many languages' sort and splice change the list
  they are called on.
- **Confusing a binding that cannot be reassigned with a value that cannot change.** The binding is
  constant; the object it names may not be.
- **Chaining past readability.** Break the chain into named steps.
- **Reaching for reduce** when map or filter says it more clearly.
- **Nesting higher-order calls deeply** instead of composing a flat pipeline.
- **Forgetting that each step may build a new collection**, which matters on a hot path.
- **Writing your own higher-order function** where a built-in one exists.
- **Wrapping every function in a result.** Use it only where the operation can genuinely fail.
- **Returning an option when the caller needs to know why.** That is a result.
- **No way to transform the error** (no map-error), so every caller unpacks it by hand.
- **Turning results back into exceptions inside the domain**, which defeats the purpose.
- **Over-engineering simple validation.** Where exceptions are the language's idiom for it, simple
  validation may use the language's exceptions; a result is for failures the caller must handle and
  compose.
- **A sentinel for absence** (`0`, `-1`, an empty string) "just this once."
- **Reading the clock, a random source or the environment inside the core** because passing it in
  felt like extra typing.
