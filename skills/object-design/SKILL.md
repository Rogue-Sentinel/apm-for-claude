---
name: object-design
description: "Use when you design or change a type's public surface, when callers read an object's fields to decide what to do with it, when a hierarchy is getting deep or a subtype uses little of what it inherits, or when a type has reached the public-method limit and needs a stated reason."
---

# Object design

A type hides how it works and offers what it can do, assembles its behavior from parts instead of
inheriting it, and keeps a surface narrow enough that a reviewer can see why it is that wide.

## When this applies

- You are designing a type's public surface, or adding a public method to one.
- A type exposes its fields directly, or has a getter and a setter for every field that protect
  nothing.
- Code outside a type reads its state, makes a decision and writes the state back, instead of
  asking the type to act.
- The domain model is anemic: data types with no behavior, and the rules scattered across callers.
- An inheritance hierarchy is deeper than two or three levels, subtypes override many of their
  parent's methods or use only a fraction of what they inherit, or a change to a base type breaks
  subtypes far away from it (the fragile base class).
- A type needs to combine behaviors from several sources, and the hierarchy cannot express the
  combination without multiplying subtypes.
- A type has as many public methods as the profile's public-method limit, or more.
- Someone names a principle (encapsulation, information hiding, protecting invariants,
  composition over inheritance, favoring composition) and you need to apply what it says.

## The core rule

**Expose behavior, not data. Prefer "has-a" to "is-a". Keep the surface narrow, and when it is
wide, say why.** A type bundles its data with the operations on it and enforces its own rules, so
no caller can put it into an invalid state. It gets varied behavior by holding interchangeable
parts, not by subclassing, unless the "is-a" relationship is genuine, stable and permanent.

## Encapsulation

Objects hide **how** they work and expose **what** they can do. Callers interact through methods
that carry business meaning and enforce business rules; they never reach in and rearrange the
state. That protects invariants, reduces coupling, and makes refactoring safe, because nothing
outside depends on the internals.

1. **Find the exposed state**: public fields, or private fields behind trivial getters and setters.
   Look especially for outside code that reads a field, decides something, and writes back: that
   decision belongs inside the object.
2. **Find the behavior.** Ask what decisions outside code makes with this data, and move each one
   into the object as a method named for the behavior, not for the data it touches.
3. **Replace access with behavior.** `if account.balance >= amount: account.balance -= amount`
   becomes `account.withdraw(amount)`, and the object enforces its own rule.
4. **Remove the accessors no one needs any more.** Keep only those a framework genuinely requires
   (serialization, a persistence mapper), and mark them as being for that purpose.
5. **Verify** that the object enforces every invariant itself and that no outside code can put it
   into an invalid state. Run the tests.

Signs: public fields or properties with no validation; a getter and a setter for every field;
outside code that reads, decides and writes (`if order.status == "new": order.status =
"confirmed"`); feature envy, where a method uses more of another type's data than its own; objects
passed around as bags of data with no behavior; a setter that accepts an invalid state
(`account.setBalance(-100)`).

Before:

```
type BankAccount:
    public balance: number
    getBalance(): return balance
    setBalance(b): balance = b

// a caller makes the decision the account should own
if account.getBalance() >= amount:
    account.setBalance(account.getBalance() - amount)
```

After:

```
type BankAccount:
    private balance: number

    withdraw(amount):
        if amount > balance: return Failure(InsufficientFunds)
        balance = balance - amount
        return Success

    hasAvailableFunds(amount): return balance >= amount
```

**Tell, don't ask**: rather than asking an object for its data and acting on it, tell it what to
do. A value type that is inherently data (a point, an amount of money, a color) may expose its
values for reading; even then, a named query (`availableBalance()`) beats a generic getter. The
field and behavior checks, the smells encapsulation fixes, the tell-don't-ask table and when a
getter is fine are in
[references/encapsulation-checklist.md](references/encapsulation-checklist.md).

## Composition over inheritance

Inheritance couples a child tightly to its parent: a change to the base type ripples through the
whole hierarchy, often in ways no one expected (the **fragile base class** problem). Composition
assembles behavior from independent, interchangeable parts. **Prefer "has-a" over "is-a"**, unless
the "is-a" is genuine, stable and permanent.

1. **Find the problem in the hierarchy**: deep (more than two or three levels), wide (many subtypes
   each overriding different behaviors), or rigid (you need a combination of behaviors it cannot
   express).
2. **List the behaviors** that vary across it. Each is a candidate component or strategy.
3. **Extract each behavior** into its own type behind an interface, and move its logic out of the
   base type or subtypes into the component.
4. **Compose at run time.** The original type holds references to its components, injected through
   its constructor. Different combinations give different behavior with no new subtypes.
5. **Verify** that the composed behaviors work together, run the tests, and confirm that a new
   combination needs no new type.

Signs: inheritance more than three levels deep; subtypes that override most of their parent's
methods; a "diamond", or wishing for multiple inheritance; subtypes that use only a fraction of
their parent's surface; a combinatorial explosion of subtypes (`FastRedCar`, `SlowRedCar`,
`FastBlueCar`...); a change to a base type that breaks distant subtypes.

Before:

```
type Animal:              move()
type FlyingAnimal extends Animal:   move(): fly
type SwimmingAnimal extends Animal: move(): swim
// a duck flies and swims: single inheritance has no good answer
```

After:

```
interface Movement:
    move()
Flying implements Movement:   move(): ...fly...
Swimming implements Movement: move(): ...swim...

type Animal:
    constructor(movements: list of Movement)
    move(): for each movement in movements: movement.move()

duck = new Animal([new Flying(), new Swimming()])
```

Inheritance is still right for a genuine, stable "is-a", for sharing an implementation across two
or three closely related types, and where a framework requires it. Composition also keeps a
subtype from breaking its parent's contract (`apm:solid`, Liskov substitution). The strategy,
decorator, delegation and mixin patterns, the table of when inheritance is still appropriate and
the decision steps are in [references/composition-patterns.md](references/composition-patterns.md).

## Seven or more public methods

**A type with 7 or more public methods needs a stated reason in review.** The number is the
profile's `standard.limits.public_methods` (default 7); a project may set its own, and raising it
is reported as a loosened limit, like any other limit (`apm:clean-code`).

- **Why the rule exists.** A wide surface is the large-class smell from the outside: it usually
  means more than one responsibility (`apm:solid`, single responsibility), or clients that each use
  a different slice of it (interface segregation). Every public method is also a promise that is
  hard to take back.
- **Wide is not automatically wrong.** A facade over a subsystem, a value type with many small
  queries, or a port whose role genuinely has that many operations can be right. The rule is not
  "never"; it is that **the reason is written down where a reviewer will see it.**
- **What counts.** Every method a caller outside the type can call. Constructors and the
  language's special methods do not count; neither do private helpers. `apm metrics` lists the
  types it can count as wide types, and where it can count them, a newly wide type shows up in the
  debt check like any other new item.
- **Stating the reason.** Put a short comment at the type's declaration saying what the type is and
  why its surface is this wide ("Facade over the billing subsystem; each method is one use case"),
  and repeat the reason in the change's review notes. A worker who cannot state a reason reports
  that to the manager instead of shipping the type.
- **No reason?** Split the type. Group its methods by stakeholder and by client, extract each group
  (`apm:refactoring`), and give each client the narrowest interface it needs.

Pseudo-code of the review check:

```
for each type in changedTypes:
    if publicMethodCount(type) >= limits.publicMethods:
        if no stated reason at the declaration or in the review notes:
            finding("needs a stated reason, or a split", type)
```

## References

- [references/encapsulation-checklist.md](references/encapsulation-checklist.md): field and
  behavior checks, design smells, tell-don't-ask, and when getters are fine.
- [references/composition-patterns.md](references/composition-patterns.md): strategy, decorator,
  delegation and mixins, when inheritance is still right, and the decision steps.

## Common mistakes

- **Adding a getter and a setter for every field** by reflex.
- **Returning a mutable collection** the type owns. Return a copy or a read-only view.
- **Leaking the internal structure** through a debug or text representation that callers parse.
- **Breaking encapsulation "just for the tests."** A test that needs the internals is telling you to
  redesign: test through behavior, or extract the part it wants to reach.
- **Over-encapsulating a simple value type.** Plain read access to a point's coordinates is fine.
- **Avoiding all inheritance on principle.** Shallow, simple hierarchies with a genuine "is-a" are
  fine.
- **Too many tiny components** that are hard to assemble and harder to follow.
- **Losing a genuine "is-a"** in a tangle of parts when the relationship really was stable.
- **Components with no interface** defining their contract.
- **Composing without injection**: hard-coding the components inside the type, so they cannot be
  swapped or faked.
- **Shipping a wide type with no reason**, or raising `standard.limits.public_methods` to make the
  flag go away.
