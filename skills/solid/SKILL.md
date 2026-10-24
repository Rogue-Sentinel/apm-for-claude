---
name: solid
description: "Use when you add or change a type, a module or an interface, when a type does too much or a new case means editing a growing conditional, when a subtype or a fake behaves differently from what its callers expect, or when business logic reaches for a concrete database, network or file system. Also use when the request mentions SRP, OCP, LSP, ISP or DIP, single responsibility, open-closed, Liskov substitution, interface segregation, dependency inversion, separation of concerns, multiple reasons to change, fat interfaces, depending on abstractions, decoupling, or inheritance hierarchies."
---

# SOLID

Five rules for where behavior lives, so that a change lands in one place, new cases are added
rather than edited in, and every dependency points at something stable.

## When this applies

- You are adding a type, a module or an interface, or changing what one is responsible for.
- A type or module seems to do "too many things", serves several stakeholders, or several people
  edit it for different reasons.
- A change to one feature forces edits in unrelated code, or a new feature means editing code that
  already works and is tested.
- A switch or if-else chain grows with every new requirement, or the system needs plugin-like
  extension points.
- You are designing or reviewing an inheritance hierarchy, a subtype overrides a method in a way
  that changes what callers expect, substituting a subtype causes errors, or code checks a value's
  concrete type before calling it.
- An interface has methods that some implementations leave empty or make fail, clients call only a
  few of its methods, a change to one of its methods forces unrelated clients to rebuild or
  retest, or a fake in a test implements many methods to exercise one.
- Business logic names a concrete database driver, network client or file system call; swapping a
  piece of infrastructure means editing business rules; a unit test needs heavy mocking or a running
  external system; or a module cannot be reused because it is welded to its infrastructure.
- Test setup is complicated because the type under test has many dependencies.
- Someone names a principle (single responsibility, separation of concerns, open-closed,
  Liskov substitution or behavioral subtyping, interface segregation or fat interfaces,
  dependency inversion or decoupling) and you need to apply what it says.

## The core rule

**Each type has one reason to change; new behavior is added as new code; every subtype keeps its
parent's promises; every client depends only on what it uses; and policy depends on abstractions
it owns, never on the details that implement them.**

Apply them to variation you can see, not variation you imagine. Do not abstract on the first case.
Write it concretely; when a second case arrives, consider the abstraction; by the third the shape
is clear (the rule of three, in [references/ocp-strategies.md](references/ocp-strategies.md)). An
abstraction with one implementation and no test fake is usually speculative generality.

## Single responsibility

A type, module or function has **one, and only one, reason to change**. A reason to change is a
stakeholder or a business capability: when one type serves several, a change one of them asks for
can break what another relies on. Separate the responsibilities so that change is isolated.

1. **List what it does.** Group its methods by the stakeholder or capability they serve. More than
   one group means more than one responsibility.
2. **Name each group** in domain terms. A group you can only name in technical terms (logging,
   persistence, formatting) is an infrastructure concern mixed into business logic.
3. **Extract each group** into its own type with a focused, cohesive surface. The original
   delegates to the new types, or is replaced by them.
4. **Verify independence.** Change one responsibility and confirm that no other type has to
   change. Run the tests. If a change in one forces a change in another, the split was not clean.

Signs: more than 5–7 public methods serving different purposes (at the profile's public-method
limit, a reason is owed anyway: see `apm:object-design`); methods that use disjoint sets of the type's
fields; a name with "And" in it, or a vague noun (`UserManagerAndValidator`); tests of one feature
that need setup for an unrelated one (testing email needs a database); several people editing the
same type for different reasons; imports from many unrelated modules.

Before:

```
type Employee:
    calculatePay()       // the payroll department asks for these changes
    generateReport()     // the reporting team asks for these
    saveToDatabase()     // the persistence owners ask for these
```

After:

```
type PayCalculator:      calculatePay(employee)
type EmployeeReporter:   generateReport(employee)
type EmployeeRepository: save(employee)
```

"One responsibility" does not mean "one method": a type has as many methods as its single
responsibility needs. The quick assessment, the naming, structural and change red flags, the table
of common responsibilities, and the extract-class, extract-interface and split-by-layer strategies
are in [references/srp-indicators.md](references/srp-indicators.md).

## Open-closed

A module is **open for extension and closed for modification**: when requirements change, new
behavior arrives as new code (a new type, a new module, a new entry), not as edits to code that
already works. That protects tested code from regression and lets two people extend the system at
once without colliding.

1. **Find the variation point**: the place that changes whenever a new case arrives. If a new
   payment type means editing `processPayment`, that function is it.
2. **Define an abstraction** that captures exactly the behavior that varies. The existing code
   depends on it instead of on the concrete cases.
3. **Implement one variant per case** behind the abstraction. Existing variants stay untouched.
4. **Choose the variant in one place**: a factory, a registry, injection, or configuration picks
   the implementation at run time.
5. **Verify** by adding a new variant: only a new type and its registration should be needed, with
   no edit to existing code. Run all the tests.

Signs: a new type means editing a switch or if-else chain; one new feature changes several places;
existing tests break when unrelated functionality is added; a boolean parameter selects between two
behaviors; the same conditional repeats across several functions.

Before:

```
function area(shape):
    if shape.kind == "circle":    return PI * shape.radius * shape.radius
    if shape.kind == "rectangle": return shape.width * shape.height
    // every new shape edits this function
```

After:

```
interface Shape:
    area() -> number

Circle implements Shape:
    area(): return PI * radius * radius
Rectangle implements Shape:
    area(): return width * height

// a triangle is a new type; nothing above changes
```

The mechanics of this move are `apm:refactoring` (replace conditional with polymorphism). The five
strategies (polymorphism, decoration, configuration, events and plugins, injection), how to choose
between them, and the rule of three are in
[references/ocp-strategies.md](references/ocp-strategies.md).

## Liskov substitution

If `S` is a subtype of `T`, then anywhere a `T` is used an `S` can be used instead **without
changing the correctness of the program**. A subtype keeps its parent's contract:

- **Preconditions are the same or weaker**: it accepts everything the parent accepts.
- **Postconditions are the same or stronger**: it guarantees at least what the parent guarantees.
- **Invariants are preserved**: it does not break the rules the parent's type maintains.

When a subtype breaks the contract, polymorphism becomes unreliable and every caller has to know
which subtype it really holds.

1. **Write down the base contract**: what callers must satisfy, what each method guarantees, and
   what always holds true of the type.
2. **Check every override in every subtype** against those three rules.
3. **Test substitutability**: write the contract tests against the base type, then run them
   unchanged against every subtype. All of them must pass.
4. **Fix a violation by changing the design, not the test.** A subtype that cannot keep the
   contract should not extend that base: use composition (`apm:object-design`) or reshape the
   hierarchy.

Signs: a subtype fails where its parent does not; a subtype ignores a parent method or makes it do
nothing; code checks the concrete type before calling a method; a subtype validates its input more
strictly than its parent; an override returns a different kind of value, or none, where the parent
returns one; an "is-a" relationship that feels forced ("is a square a rectangle?").
(Examples by language: [references/examples-by-language.md](references/examples-by-language.md).)

Before:

```
type Bird:
    fly()                          // moves through the air
type Penguin extends Bird:
    fly(): fail "penguins cannot fly"
// any code written against Bird.fly() breaks when handed a Penguin
```

After:

```
type Bird:
    move()
type FlyingBird extends Bird:
    move(): fly
type Penguin extends Bird:
    move(): swim or walk
// every Bird can move(); how it moves varies
```

This rule binds test doubles too: a fake or a stub that does not keep the interface's contract
makes the tests prove the wrong thing. Run the same contract tests against the fake. The four
classic violations (strengthened precondition, weakened postcondition, broken invariant, a new
failure), each with its fix, and the substitution test are in
[references/lsp-violations.md](references/lsp-violations.md).

## Interface segregation

**No client is forced to depend on methods it does not use.** A large, general interface couples
unrelated clients: when one client needs a change to it, every other client is affected, though
none of them call the changed method. Split a fat interface into small interfaces named for the
roles clients play.

1. **Find the fat interface**: many methods, different clients using different subsets, and
   implementations that leave methods empty or make them fail.
2. **Group the methods by client.** Methods always used together form a group; each group is a
   candidate interface.
3. **Define a role interface per group**, named for the role: `Readable`, `Writable`, `Closeable`
   rather than one `FileOperations`.
4. **Update the implementations.** A type now implements the role interfaces it genuinely supports,
   and may implement several.
5. **Update the clients.** Each depends on the smallest interface that covers its needs: change the
   parameter and field types that name the fat interface.

Signs: an interface of more than five to seven methods; implementations with empty bodies or a
"not implemented" failure; tests that fake many methods but exercise one; clients that take the
interface but call one or two of its methods; a change to the interface that forces unrelated code
to rebuild or retest.

Before:

```
interface Worker:
    work()
    eat()
    sleep()
// a Robot is a Worker, but cannot eat() or sleep()
```

After:

```
interface Workable:  work()
interface Feedable:  eat()
interface Restable:  sleep()

Human implements Workable, Feedable, Restable
Robot implements Workable
```

The goal is grouping by client, not the fewest methods per interface. The role, composition and
legacy-adapter patterns, the sizing guide and the over-segregation test are in
[references/isp-patterns.md](references/isp-patterns.md).

## Dependency inversion

**High-level modules do not depend on low-level modules; both depend on abstractions.
Abstractions do not depend on details; details depend on abstractions.** Instead of business logic
calling a database driver, the business logic declares the interface it needs, and the low-level
module implements it. The high-level module becomes stable and reusable, and the infrastructure
becomes swappable. This is the rule `apm:clean-architecture` builds its layers on.

1. **Draw the dependency arrows.** A domain or business type that imports a concrete
   infrastructure type (database, network, file system) points the wrong way.
2. **Define the abstraction the high-level module needs**, named from its point of view:
   `OrderRepository`, not `SqlClient`. **The interface belongs to the high-level module** and lives
   beside it.
3. **Implement it in the low-level module.** The implementation lives with the infrastructure and
   imports the interface from the domain.
4. **Inject the implementation**, through the constructor or a factory. The high-level module never
   constructs its low-level dependency itself.
5. **Verify**: the high-level module builds and its tests run with no infrastructure at all, using a
   simple in-memory or stub implementation.

Signs: business logic that imports a database driver, an HTTP client or the file system module
directly; a constructor that creates its own dependencies (`this.db = new SqlClient()`); a type that
cannot be tested without a running database or network; moving from one database to another means
editing business logic; domain types that import framework types.
(Examples by language: [references/examples-by-language.md](references/examples-by-language.md).)

Before:

```
type OrderService:
    constructor():
        db = new SqlClient()                 // reaches straight for the low-level module
    placeOrder(order):
        db.query("INSERT INTO orders ...")
```

After:

```
interface OrderRepository:                   // owned by the domain
    save(order)

type OrderService:
    constructor(repository: OrderRepository) // depends on the abstraction
    placeOrder(order):
        repository.save(order)

SqlOrderRepository implements OrderRepository:
    save(order): ...the SQL lives here...
```

Not everything is inverted: the standard library, value types and the domain's own entities are
stable and are used directly. Constructor injection, interface ownership, the composition root, the
factory function, the table of when not to invert and the direction rule are in
[references/dip-patterns.md](references/dip-patterns.md).

## How the five fit together

| Symptom | Start with | Then |
|---------|-----------|------|
| A type changes for several reasons | single responsibility | interface segregation for its clients |
| A new case edits a working function | open-closed | `apm:refactoring` for the move |
| A subtype or fake surprises its callers | Liskov substitution | `apm:object-design` (composition) |
| Clients carry methods they never call | interface segregation | Liskov, for empty implementations |
| Logic needs infrastructure to run | dependency inversion | `apm:clean-architecture` |

## References

- [references/srp-indicators.md](references/srp-indicators.md): the quick assessment, red flags,
  responsibility categories and splitting strategies.
- [references/ocp-strategies.md](references/ocp-strategies.md): five ways to stay open for
  extension, how to choose, and the rule of three.
- [references/lsp-violations.md](references/lsp-violations.md): the four classic violations with
  fixes, and the substitution test.
- [references/isp-patterns.md](references/isp-patterns.md): role interfaces, composing them,
  adapting a fat interface you do not own, and sizing.
- [references/dip-patterns.md](references/dip-patterns.md): injection, interface ownership, the
  composition root, factories, and when not to invert.
- [references/examples-by-language.md](references/examples-by-language.md): the names the original
  skills used as examples, by language.

## Common mistakes

- **Splitting too far**: every method in its own type, or one interface per method. Group by
  responsibility and by client, not by method count.
- **Reading "does one thing" as "has one method."** A type can have several methods if they all
  serve the same responsibility.
- **A coordinator that delegates everything and owns nothing**: a god type in disguise.
- **Letting a "small" type grow** one responsibility at a time because it was small.
- **Abstracting before the variation is real.** Wait for the second case; build for the third.
- **Strategy objects for every if-else.** Two stable branches are fine as they are.
- **Forgetting the factory or registry**: something still has to choose the implementation.
- **Abstractions that leak** their implementation's details, or that mirror the implementation's
  API instead of the caller's need.
- **Designing for extensions that never come.**
- **Inheriting to reuse code** rather than to express a behavioral subtype. The geometric "is-a"
  (a square is a rectangle, a circle is an ellipse) is not a behavioral one.
- **A subtype method that fails with "not implemented"**, or an override whose return breaks callers.
- **Fakes and stubs that do not honor the interface's contract**, so the tests pass against
  something production never does.
- **Splitting interfaces that are always used together**, or segregating an interface that has only
  one client (you will not need it yet).
- **Splitting the interface but not the clients**: they still take the fat one.
- **Putting the interface with the infrastructure** instead of with the module that needs it.
- **Inverting stable dependencies** (the standard library's arithmetic, value types) for no gain.
- **Reaching for an injection framework** where passing the dependency to the constructor would do.
- **Not actually inverting**: declaring an interface but still importing the concrete type.
