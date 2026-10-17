---
name: refactoring
description: "Use when a function or file you need to change is over a limit, when a change touches existing debt, or when you are extracting a method, renaming, splitting a file or replacing a type-based conditional, so the structure changes without the behavior changing."
---

# Refactoring

Change the structure of code without changing what it does, in small verified steps, in commits
that hold nothing else.

## When this applies

- A function or file you need to change is already over its limit.
- The change you are about to make touches existing debt.
- A function is longer than 10 to 15 lines of logic, mixes levels of abstraction, or has a comment
  explaining what its next block does.
- A name is unclear, misleading or out of date.
- A switch or if-else chain branches on a type, status or kind, especially the same chain in
  several places.
- A file needs splitting.

## The core rule

**Refactoring never changes behavior**, and the proof is the same tests passing before and after.
Have the tests first: if the code you are about to restructure is not pinned by tests, write those
tests before you move anything (`apm:test-first`). Then take one structural step at a time and run
the tests after each.

## Extract before you add

**A function or file over its limit is not somewhere to put new code.** Split it first, in its own
commit, then add the feature to the smaller piece. One cohesive unit per file.

This is a rule because it was broken. A project's plan named its largest file (1,668 lines) as
already the biggest in the repository and said, in so many words, to move content out of it rather
than add to the pile. Five features went into it instead, and it reached **2,617 lines** before
anyone stopped. Each one was harder to write than the last, and each made the next worse. The
features shipped and the structural half of the plan was quietly dropped, which is not shipping
the plan. So, in order:

1. **A plan's structural constraints are acceptance criteria.** File size, layering, "move, don't
   add", and every document the plan promises are part of the work, not a preamble to it. (That
   plan also called for three decision records. None were written. See `apm:adr`.)
2. **If a constraint is wrong or too expensive, say so and get a decision.** A worker reports it to
   the manager; the manager asks the user. Silently skipping the constraint and delivering the
   features is exactly the failure this rule exists to prevent.
3. **Refactor and behavior never share a commit** (below).
4. **Logic does not move sideways** (below).

In a plan, this shows up as its own task: "extract X from Y" lands, verified, before the task that
adds to it.

## Refactor and behavior never share a commit

A refactoring commit is a **pure move**: the same tests pass on either side of it, unchanged. A diff
that only moves code can be reviewed in a minute; mixing a fix or a feature into it makes both
unreviewable, because the reader can no longer tell which lines changed meaning.

- Commit the refactoring, run the suite, then commit the behavior change separately.
- If you find a bug while refactoring, finish or back out the refactoring commit first, then fix the
  bug test-first in its own commit.
- A test that must change for a refactoring to pass means the refactoring changed behavior, or the
  test was coupled to structure. Stop and decide which; do not edit the test to fit.
- A cleanup under the boy scout rule is small enough to ride along; anything larger is a refactoring
  and gets its own commit.

## Logic does not move sideways

When you split something out, the **decisions** go to tested logic, not into the new file beside
them. When a presentation unit (a screen, a view, a page, a handler) comes out of a larger one,
anything in it that is not presentation (a decision, a format, a sort, a calculation) moves to a
tested model, and the presentation becomes a thin function that draws from a read-only snapshot
and posts what it wants done as an action. A change to it then comes with a test of what it posts,
and everything it decides is tested in the model.

The same holds at every edge: an entry point, an adapter or a controller that grew a decision has
that decision extracted into the core, where a fast test covers it. Moving untested logic into a
new file is not a refactoring that pays debt; it relocates it. See `apm:clean-architecture`.

## Extract method

If a block needs a comment to explain what it does, the block should be a function whose name
replaces the comment. Extract until each function does one thing at one level of abstraction.

1. **Find the candidate:** a block set off by a blank line or a comment, a body nested in a loop or
   conditional, or duplicated logic. It has one clear purpose.
2. **Name it** for *what* it does, not how: `calculateTotal`, `validateInput`, `formatAddress`. If
   you cannot name it, it is doing too much, or you do not understand it yet.
3. **Find its inputs and outputs.** Variables the block reads become parameters; variables it writes
   become the return value. More than three parameters means decompose further or introduce a
   parameter object.
4. **Extract and replace.** Move the block into the new function and call it from where it was.
   Every variable is resolved through a parameter or the return value.
5. **Verify.** Run the tests. Behavior must not change; a failure means the extraction broke
   something, usually parameter passing or scope.

Before:

```
function processOrder(order):
    // validate order
    if order.items is empty:
        fail "Order must have items"
    if order.customer is missing:
        fail "Order must have customer"

    // calculate total
    total = 0
    for item in order.items:
        total = total + item.price * item.quantity
    if order.discount:
        total = total * (1 - order.discount)

    // send confirmation
    emailService.send(order.customer.email, "Total: " + total)
```

After:

```
function processOrder(order):
    validateOrder(order)
    total = calculateTotal(order)
    sendConfirmation(order.customer, total)
```

When to extract (the comment, indent, reuse, abstraction-level and testability heuristics), naming
rules, the parameter table and the step checklist are in
[references/extraction-heuristics.md](references/extraction-heuristics.md).

## Rename

A name that misleads is a defect waiting to happen; renaming is the cheapest refactoring there is.
How to choose the name is in `apm:clean-code` (meaningful names). The mechanics:

1. Rename with the editor's rename refactoring, or a search that you check hit by hit. Text search
   alone misses and over-matches.
2. Update every reference: tests, configuration, documentation, log and error messages that name
   it, and API boundaries.
3. A name that crosses a published boundary (a public API, a stored format, a configuration key) is
   a behavior change for its users: treat it as a decision, not a cleanup.
4. Run the tests, confirm nothing was missed, and read the new name in context.
5. Commit the rename on its own.

## Replace conditional with polymorphism

When a conditional selects behavior by type, give each type its own implementation of a shared
interface. The conditional disappears, the right behavior is chosen by the object, and a new type
is added without editing the existing ones (open for extension, closed for modification).

1. **Find the conditional:** a switch or if-else chain on type, status, category or kind. The same
   chain repeated in several functions is the strongest signal.
2. **Define the interface** from the common shape of the branches.
3. **Create one implementation per branch**, and move that branch's logic into it.
4. **Replace the conditional with dispatch:** call the interface method on the right object, chosen
   once, at construction, by a factory or a registry.
5. **Verify:** run the suite, and add a test per variant confirming it matches the old branch.

Signs: a switch with more than 3 cases; type checks or string comparisons on a kind; the same switch
in several places; adding a type means editing several files; comments like "if premium, do X; if
basic, do Y".

Before:

```
function calculateShipping(order):
    switch order.type:
        "standard":  return order.weight * 5.0
        "express":   return order.weight * 10.0 + 15.0
        "overnight": return order.weight * 20.0 + 30.0
```

After:

```
interface ShippingStrategy:
    calculate(order) -> number

StandardShipping implements ShippingStrategy:
    calculate(order): return order.weight * 5.0
ExpressShipping implements ShippingStrategy:
    calculate(order): return order.weight * 10.0 + 15.0
OvernightShipping implements ShippingStrategy:
    calculate(order): return order.weight * 20.0 + 30.0

// usage: order.shippingStrategy.calculate(order)
```

**Not every conditional earns it.** Two simple branches are fine as they are. Pure data mapping
wants a lookup table, not classes. A temporary condition (a feature flag) will be removed anyway.
On a measured hot path, dispatch has a cost. Use the decision checklist and the longer examples
(payments, notifications, a registry as factory) in
[references/polymorphism-before-after.md](references/polymorphism-before-after.md).

## Splitting a file

A file over the limit is split by responsibility, as a pure move, in its own commit.

1. Find the seams: groups of functions that share data and change for the same reason. Each group
   is a candidate file; the smell names (divergent change, large class) say where to cut.
2. Move one group at a time, keeping the public surface stable, and run the tests after each move.
3. Apply "logic does not move sideways": a decision found in a presentation or edge file goes to
   tested logic, not to the new file.
4. **Every part must land under the file limit.** Splitting one over-limit file into two over-limit
   files raises the count of long files, and the debt ratchet fails it. Split further. If the parts
   genuinely cannot get under the limit in this work, that is a decision: report it (a worker to
   the manager, the manager to the user) instead of landing the split.
5. A pure move of a long function into the new file is not new debt to the ratchet, as long as it
   does not grow on the way.

## References

- [references/extraction-heuristics.md](references/extraction-heuristics.md): when and how to
  extract, naming rules, parameter counts, and the extraction checklist.
- [references/polymorphism-before-after.md](references/polymorphism-before-after.md): longer
  before-and-after examples, when not to use polymorphism, and the decision checklist.

## Common mistakes

- **Adding to an over-limit file "for now"**, planning to split later. Later never comes; that is
  how a file reaches 2,617 lines.
- **Dropping a structural constraint silently** because it was inconvenient. Ask.
- **A refactoring commit that also fixes a bug** or changes behavior.
- **Moving logic sideways** into the new file instead of into tested logic.
- **Extracted functions that still need many parameters.** Decompose further.
- **Naming after the mechanism** (`loopOverItems`) instead of the purpose (`calculateTotal`).
- **Extracting too little**: a one-liner that adds no clarity.
- **Breaking variable scope** without adjusting the parameters.
- **Extracting into another type** when the function should stay local.
- **Renaming without updating every reference**, tests included, or with synonyms used
  inconsistently afterward.
- **Polymorphism for a trivial or never-growing conditional**, or where a lookup table would do.
- **Forgetting the factory or registry** that picks the implementation.
- **A split that leaves two over-limit files.**
