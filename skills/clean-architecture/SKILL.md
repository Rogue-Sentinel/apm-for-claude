---
name: clean-architecture
description: "Use when a change crosses a layer, adds a dependency or an import between modules, puts business logic near a framework, a database, the network or the user interface, or connects the code to an outside system, so the core stays independent and is tested without them."
---

# Clean architecture

The core of the system holds the decisions and depends on nothing outside it. Frameworks,
platforms and input and output live only at the edges, behind interfaces the core owns, so the core
is tested directly, fast, with nothing running.

## When this applies

- A change crosses a layer, or adds a dependency or an import from one module to another.
- Business logic is tangled with database, network, messaging, platform or framework code, or lives
  inside a controller, a handler, an entry point or a screen.
- Swapping a technology (a database, a queue, an outside provider) would mean rewriting business
  logic, or upgrading a framework means editing business rules.
- Testing the business logic needs a database, a network, a running platform or a person.
- The domain model mirrors a database schema or an outside system's format instead of business
  concepts, carries serialization or persistence annotations, or extends a framework's base types.
- Business logic changes whenever an outside system's contract changes.
- There is no clear line between "what the system does" and "how it connects to the world."
- Someone names an idea from this skill (hexagonal architecture, ports and adapters, clean
  architecture boundaries, domain isolation, an anti-corruption layer, keeping the domain pure) and
  you need to apply it.

## The core rule

**Every dependency points inward, toward the domain. Frameworks, platforms and input and output
are hard dependencies only at the edges.** The domain imports nothing from the outside; it declares
the interfaces (ports) it needs, and the edges implement them (adapters). Because the core touches
nothing outside itself, the large majority of the code is tested directly, with fakes in place of
the world, in milliseconds. That is what makes test-first possible (`apm:test-first`): **an
architecture whose core cannot be tested without its platform is the first thing to fix.**

## The dependency rule

```
   entry points and adapters  (frameworks, platform, database, network, presentation)
             |
             v
   application  (use cases: coordinate the domain through ports)
             |
             v
   domain  (entities, values, rules, and the port interfaces)
```

1. **The domain imports nothing** from adapters, frameworks or the platform: only the language's
   standard library and its own types.
2. **Adapters import from the domain**: its port interfaces and its model.
3. **The composition root imports everything** and wires the concrete adapters to the ports, at the
   program's entry point. Only it knows the concrete types.
4. **The port interfaces belong to the domain.** They are owned by the code that needs them, not by
   the code that provides them (`apm:solid`, dependency inversion).
5. **A decision never lives at the edge.** Entry points, adapters and the presentation layer
   translate, forward and draw; the choices live in tested logic behind them. An edge that grows a
   decision has it extracted into the core (`apm:refactoring`, logic does not move sideways).

What this looks like in practice: the platform's or framework's interface is included in the
adapter layer and nowhere else, and the rest of the code (typically most of it) has no such import
at all, so it builds and runs its tests without the platform present.

## Ports and adapters

The domain sits at the center and defines **ports**: interfaces describing what it offers to the
outside (**driving** ports, inbound) and what it needs from it (**driven** ports, outbound).
**Adapters** implement those ports for a specific technology. The domain never imports
infrastructure code.

1. **Find the domain core**: what the system does regardless of any technology. Business rules,
   validation, calculations and state machines belong here.
2. **Define the driving ports**: the use cases the system offers, as interfaces or use-case types:
   `PlaceOrder`, `RegisterUser`, `GenerateReport`. Outside actors (an HTTP controller, a
   command-line handler, a message consumer, the user interface) call them.
3. **Define the driven ports**: what the domain needs, as interfaces: `OrderRepository`,
   `PaymentGateway`, `NotificationSender`, `Clock`. The domain calls them; infrastructure implements
   them.
4. **Write an adapter for each port.**
   - **Driving adapters** (inbound): an HTTP controller, a query resolver, a command-line handler,
     a message consumer, a platform callback.
   - **Driven adapters** (outbound): a SQL repository, a payment provider's gateway, an email
     sender, the platform's state readers and writers.
5. **Wire them at the composition root.** The domain never knows which concrete adapter is plugged
   in.

Signs: domain types that import a web framework, a database driver or an HTTP client; business
logic inside controller or handler functions; a database query change that touches business rules;
domain unit tests that need a database connection; no clear separation between what the system does
and how it talks to the world.

Before:

```
type OrderController:
    placeOrder(request, response):
        items = request.body.items
        total = sum of item.price for item in items
        if total < 10: return response.status(400).json({ error: "minimum order is 10" })
        sql.query("INSERT INTO orders ...")
        smtp.send(request.body.email, "Order confirmed")
        response.json({ status: "ok" })
```

After:

```
// domain: the ports
interface OrderRepository:    save(order)
interface NotificationSender: sendConfirmation(email, order)

// application: the use case
type PlaceOrder:
    constructor(orders: OrderRepository, notifier: NotificationSender)
    execute(items, customerEmail) -> Result of (Order, OrderError):
        order = Order.create(items)          // the domain enforces the minimum
        if order is Err: return order
        orders.save(order.value)
        notifier.sendConfirmation(customerEmail, order.value)
        return order

// adapters
SqlOrderRepository implements OrderRepository: ...
SmtpNotificationSender implements NotificationSender: ...

type OrderHttpController:
    constructor(placeOrder: PlaceOrder)
    handle(request, response):
        result = placeOrder.execute(request.body.items, request.body.email)
        result.match(
            ok:  order -> response.json({ status: "ok", orderId: order.id }),
            err: error -> response.status(400).json({ error: error.message }))
```

Not every small data-entry application needs every layer: the rule that never relaxes is that a
decision has a test that runs without the outside world. The conceptual model, the port and adapter
tables, a directory layout, the dependency rules and the testing strategy are in
[references/port-adapter-anatomy.md](references/port-adapter-anatomy.md).

## Domain isolation

The domain model is the business's concepts and rules in their plainest form. It is not
contaminated by database schemas, serialization formats, outside APIs or framework conventions. An
**anti-corruption layer** translates between the domain's language and each outside system's, so
the domain stays stable when the outside changes.

1. **Audit the domain's dependencies.** Any import of infrastructure, a framework or an outside
   library is a boundary violation. The domain depends only on the standard library and its own
   types.
2. **Find the contamination**: persistence or serialization annotations on domain entities,
   framework base types, an outside API's types used in domain logic, database column names
   shaping domain field names.
3. **Give each boundary its own model.**
   - The **domain model**: plain business objects.
   - The **persistence model**: records that map to the storage's tables or documents.
   - The **API model**: data-transfer types matching an outside contract.
   Mappers translate between them, at the boundary.
4. **Build the anti-corruption layer.** For an outside system whose model differs from yours, an
   adapter implements a domain port and translates the outside concepts into the domain's language.
5. **Verify the isolation**: the domain builds with no infrastructure dependency, and its tests need
   no database, network or framework. Run the tests.

Signs: domain entities carrying persistence or serialization annotations; domain types extending a
framework's base types; business logic that names tables, columns or an outside API's fields;
domain methods that take or return HTTP request or response objects; domain files importing
persistence, HTTP or serialization libraries; domain field names that match database columns
rather than business terms.

Before:

```
@StoredAs("orders")
type Order:
    @Column("order_total") order_total: number    // database naming leaks in
    @Json("cust_email") customerEmail: text        // API naming leaks in
    save(): database.save(self)                    // persistence inside the domain
```

After:

```
// domain: plain
type Order:
    total: Money
    customerEmail: EmailAddress
    applyDiscount(discount: Percentage): total = total.reduceBy(discount)

// persistence model: separate, at the edge
@StoredAs("orders")
type OrderRecord:
    @Column("order_total") orderTotal: number
    @Column("cust_email")  customerEmail: text

// mapper: at the edge
type OrderMapper:
    toDomain(record: OrderRecord) -> Order
    toRecord(order: Order) -> OrderRecord
```

Isolation pays most in a complex domain; for a trivial one, the mapping overhead may not, and that
judgment is worth an ADR (`apm:adr`). The adapter-and-mapper, separate-models and facade patterns,
the mapping strategies and the boundary rules are in
[references/anti-corruption-layer.md](references/anti-corruption-layer.md).

## Testing at the edges

Because the core has no hard dependency on the platform, **the test suite runs everything above
it**. What it does not run is the thin layer of adapters, and that layer holds no decisions.

- **Outside state reaches the core through ports, never by direct calls.** Each port has a
  production implementation that wraps the platform or the outside system, and a test
  implementation: an in-memory store, a fixed clock, or a fake that **replays a scripted sequence of
  samples**. With that, a whole real-world scenario (a session from start to finish, including its
  rare events and edge cases) becomes a deterministic unit test that runs in milliseconds.
- **Writing is the same.** Whether a write is needed at all is core logic, tested against a fake
  that records what it was asked to do. Only the production adapter performs the write, and it
  performs it under whatever conditions the platform imposes (a particular thread, a transaction,
  a rate limit).
- **What stays untested is only translation.** An adapter is mostly one call per function:
  convert, call, convert back. A long adapter function is debt like any other and is decomposed
  until its decisions have moved into the core. The boundary of what the suite does not run is
  written down, as a decision record (`apm:adr`).
- **The presentation layer is an edge too.** It draws from a read-only snapshot and posts actions;
  every decision it shows comes from a tested model. Where drawing itself must be tested, a
  headless driver exercises it without a real window, and a change to a screen comes with a driver
  test of what it posts.
- **Each layer has its own kind of test.**

| Layer | Test | Runs against |
|-------|------|--------------|
| Domain | unit tests | nothing: plain values |
| Use cases | unit tests | fakes and in-memory adapters |
| Adapters | integration tests | the real infrastructure |
| The whole system | end-to-end tests | everything |

Checking against a real installation of the platform is a manual verification step, run and
reported. It is never a test that skips itself when the platform is missing (`apm:test-first`).

A scripted-sequence fake, in pseudo-code:

```
type ScriptedSensor implements SensorReadings:
    constructor(samples: list of Sample)
    next() -> Option of Sample: return samples.popFirst()

// a whole scenario as one fast test
sensor = new ScriptedSensor([takeoff, climb, cruise, hardLanding])
report = monitorSession(sensor, clock: fixedClock)
assert report.events == [HardLanding(at: hardLanding.time)]
```

## The layer map

A project's layers, and the direction each may depend on, are declared in its profile under
`standard.layers`. The auditor records them when a project is adopted; a fresh project agrees them
with the user before the first commit. Each layer gives its `name`, the `paths` globs it covers,
and `may_import`: the layers its files may import from. Two reserved names may appear in
`may_import`:

- `"outside"`: libraries beyond the language's standard library (frameworks, drivers, the
  platform's interface, any third-party package).
- `"*"`: every layer. A test layer needs this, because tests reach into every layer they test.

```
"standard": {
  "layers": [
    { "name": "domain",      "paths": ["src/core/**"],     "may_import": [] },
    { "name": "application", "paths": ["src/app/**"],      "may_import": ["domain"] },
    { "name": "adapters",    "paths": ["src/adapters/**"], "may_import": ["application", "domain", "outside"] },
    { "name": "entry",       "paths": ["src/main*"],       "may_import": ["adapters", "application", "domain", "outside"] },
    { "name": "tests",       "paths": ["tests/**"],        "may_import": ["*", "outside"] }
  ]
}
```

The rules:

- **The standard library is always allowed**, in every layer.
- **An import within the same layer is always allowed.**
- **An outside import is allowed only when the layer lists `"outside"`.** In the map above, the
  domain and the application cannot import a framework; the adapters and the entry point can.
- **An import of another layer is allowed only when `may_import` names that layer, or lists
  `"*"`.**
- **A file belongs to the layer whose `paths` glob matches it.** A file that two layers' globs both
  match is an error in the map, not in the file: the map is fixed first. A file that no layer covers
  is a finding (the map is incomplete, and the manager asks the user where it belongs), unless the
  file is outside the measured tree (`standard.metrics`).
- **Tests are a layer of their own**, with `may_import: ["*", "outside"]`, so a test may import
  whatever it tests and whatever test library it uses, while nothing else may import the tests.

**The reviewer checks every changed file's imports against the map.**

```
for each file in changedFiles:
    if file is outside the measured tree: continue
    matches = layers whose paths glob matches file
    if matches is empty:   finding("no layer covers this file", file); continue
    if matches has two or more: error("the map gives this file two layers", file, matches); continue
    layer = the one match

    for each dependency in importsOf(file):
        if dependency is in the standard library:
            continue                                          // always allowed
        else if dependency is an outside library:
            if "outside" not in layer.may_import:
                finding("imports an outside library", file, dependency)
        else:
            target = layerOf(dependency)
            if target == layer:
                continue                                      // same layer: always allowed
            else if "*" in layer.may_import:
                continue                                      // a test layer: every layer allowed
            else if target.name not in layer.may_import:
                finding("imports a layer it may not", file, dependency)
```

- **Changing the map is a decision, not a fix.** Allowing a new direction, or `"outside"` in a
  layer that did not have it, loosens the architecture the way raising a limit loosens the
  standard: the worker reports it, the manager asks the user, and an approved change is recorded as
  an ADR.
- A project without a map is held to the dependency rule above, and the auditor proposes one.

## References

- [references/port-adapter-anatomy.md](references/port-adapter-anatomy.md): the conceptual model,
  the kinds of port and adapter, a directory layout, the dependency rules and the testing strategy.
- [references/anti-corruption-layer.md](references/anti-corruption-layer.md): what an
  anti-corruption layer is, its three patterns, the mapping strategies and the boundary rules.

## Common mistakes

- **Putting the port interfaces with the infrastructure.** They belong to the domain.
- **Adapters that contain business logic.** An adapter translates; a decision in it is untested.
- **Over-engineering a simple application** with every layer. Keep the layers its decisions need.
- **Forgetting the composition root**: the wiring has to happen somewhere, once.
- **Domain objects that serialize or save themselves.** Serialization and persistence are adapter
  concerns.
- **One model shared across every layer** because "it is simpler", until the first schema
  migration or outside contract change.
- **Mapping overhead in a trivial domain** where isolation buys nothing.
- **An anti-corruption layer that grows into a second domain model.** Keep it thin: translation only.
- **Domain objects that know their own persistence lifecycle.**
- **Leaking storage-generated identifiers into domain identity.**
- **A test that skips** when the platform or an outside system is not present. Fake it, or make its
  absence a failure.
- **A long adapter function** left as it is because "adapters are not tested". It is debt.
- **Editing the layer map** to make a wrong-direction import pass.
