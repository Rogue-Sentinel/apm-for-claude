# Open-closed: strategies

## 1. Polymorphism (strategy, template method)

Replace the conditional with an interface and one implementation per case.

**Use when** behavior varies by type and new types are expected.

```
interface Formatter:
    format(data) -> text

JsonFormatter implements Formatter: ...
XmlFormatter implements Formatter: ...
// new: CsvFormatter implements Formatter: ...
```

## 2. Composition and decoration

Wrap existing behavior in a decorator that adds to it, behind the same interface.

**Use when** you want to layer behavior on without modifying the original.

```
interface Logger:
    log(message)

ConsoleLogger implements Logger: ...

TimestampLogger implements Logger:
    constructor(inner: Logger, clock: Clock)
    log(message): inner.log("[" + clock.now() + "] " + message)
```

## 3. Configuration and data

Move the variation into data (a table, a file, a stored setting) rather than code.

**Use when** the variants differ only in data, not in logic.

```
taxRates = { "US": 0.08, "UK": 0.20, "JP": 0.10 }

function tax(country, amount):
    return amount * taxRates[country]
// a new country is a new entry; no code changes
```

## 4. Events and plugins

Let outside code extend behavior by reacting to events or registering at hooks.

**Use when** the extensions come from separate modules or third parties.

```
type OrderProcessor:
    process(order):
        ...the core logic...
        events.publish("orderProcessed", order)    // extensions react; the core never names them
```

## 5. Dependency injection

Take dependencies through the constructor or as parameters instead of hard-coding them.

**Use when** the implementation of a dependency may change or vary.

```
type UserService:
    constructor(repository: UserRepository)    // works with any UserRepository
```

## Choosing a strategy

| Situation | Strategy |
|-----------|----------|
| Behavior varies by type | polymorphism |
| A cross-cutting concern (logging, timing, retries) | decoration |
| The variants differ only in data | configuration |
| Extensions come from outside the module | events and plugins |
| A dependency should be swappable | dependency injection |

## The rule of three

Do not abstract on the first variation: implement it concretely. When the second variation
appears, consider the abstraction. By the third, the pattern is clear, and you can abstract with
confidence.
