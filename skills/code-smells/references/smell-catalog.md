# Code smell catalog

Each smell gives **what** it is, **why it hurts** and its **fix**. The thresholds are the framework's
defaults; a project's `standard.limits` replaces them.

## Bloaters

### Long method
**What:** a function with too many lines, by default more than 15 lines of logic.
**Why it hurts:** hard to read, hard to test, and its parts cannot be reused.
**Fix:** extract method: break it into smaller, named functions.

### Large class
**What:** a type that does too much: many fields, many methods, many lines (over the file limit, or
7 or more public methods without a stated reason).
**Why it hurts:** hard to understand, breaks single responsibility, and attracts still more
responsibility.
**Fix:** extract class: split it by responsibility.

### Long parameter list
**What:** a function with more than 3 parameters.
**Why it hurts:** hard to call correctly, and the order is hard to remember.
**Fix:** introduce a parameter object, or a builder.

### Data clumps
**What:** the same group of values appears together in several places, such as `street`, `city`
and `postalCode`.
**Why it hurts:** duplication, and a missing abstraction.
**Fix:** extract a value object (`Address`).

### Primitive obsession
**What:** primitives standing in for domain concepts: a string for an email address, a number for
money.
**Why it hurts:** no validation, no behavior, and easy to confuse (dollars passed where cents were
expected).
**Fix:** create value objects: `EmailAddress`, `Money`, `PhoneNumber`.

---

## Couplers

### Feature envy
**What:** a function that uses another object's data more than its own.
**Why it hurts:** the logic is in the wrong place, so every change to the data type means a change
here too.
**Fix:** move the function to the type it envies.

### Inappropriate intimacy
**What:** two types that know too much about each other's internals.
**Why it hurts:** tight coupling; every change ripples between both.
**Fix:** move methods, extract a class, or introduce an interface between them.

### Message chains
**What:** a chain of calls: `order.getCustomer().getAddress().getCity()`.
**Why it hurts:** the caller is coupled to the shape of the whole chain.
**Fix:** hide the delegate: add `order.getShippingCity()`.

### Middle man
**What:** a type that delegates almost everything to another type.
**Why it hurts:** indirection with no value.
**Fix:** remove the middle man, or inline the class.

---

## Change preventers

### Divergent change
**What:** one type is modified for many different reasons.
**Why it hurts:** breaks single responsibility, and carries a high risk of merge conflicts.
**Fix:** extract classes, one per responsibility.

### Shotgun surgery
**What:** one change needs edits in many types across the codebase.
**Why it hurts:** one edit is easily missed, so the regression risk is high.
**Fix:** move the related logic into one type or module.

### Parallel inheritance hierarchies
**What:** adding a subtype in one hierarchy forces adding one in another.
**Why it hurts:** a hidden coupling between the hierarchies.
**Fix:** merge the hierarchies, or use composition.

---

## Dispensables

### Dead code
**What:** code that never runs: unused variables, unreachable branches, commented-out blocks,
functions nobody calls.
**Why it hurts:** noise, it misleads, and it has to be maintained.
**Fix:** delete it. Version control has the history.

### Speculative generality
**What:** abstractions, hooks or parameters that exist "just in case" and have only one user.
**Why it hurts:** complexity with no value.
**Fix:** remove the abstraction, and add it back when a second user actually needs it (you aren't
going to need it).

### Duplicate code
**What:** identical or near-identical code in several places.
**Why it hurts:** a fix must be applied everywhere, and one copy is easily missed.
**Fix:** extract method, extract class, or pull the method up.

### Lazy class
**What:** a type that does too little to justify existing.
**Why it hurts:** indirection with no value.
**Fix:** inline the class into its caller.

### Unnecessary comments
**What:** comments that restate the code, explain *what* a block does instead of *why*, or no longer
match the code.
**Why it hurts:** they go stale and then mislead, and a "what" comment hides a missing name.
**Fix:** delete the restating comment, update the stale one, and replace a "what" comment with an
extracted, well-named function.

---

## Prioritization matrix

| Impact \ effort | Low effort | Medium effort | High effort |
|-----------------|-----------|---------------|-------------|
| **High impact** | fix now | fix soon | plan it |
| **Medium impact** | fix under the boy scout rule | schedule | defer |
| **Low impact** | boy scout rule | defer | ignore |

**High impact:** smells in code that changes often.
**Low impact:** smells in stable code that is rarely touched.

Fix smells in code you are actively working on. Leave stable, rarely changed code alone.
