# Composition patterns

## 1. Strategy

Put an algorithm behind an interface, and inject it.

```
interface SortStrategy:
    sort(items) -> items
QuickSort implements SortStrategy: ...
MergeSort implements SortStrategy: ...

type DataProcessor:
    constructor(sorter: SortStrategy)
    process(data): return sorter.sort(data)
```

**Benefit:** the algorithm changes at run time without any edit to `DataProcessor`.

## 2. Decorator

Wrap an object to add behavior, keeping the same interface.

```
interface Logger:
    log(message)

ConsoleLogger implements Logger:
    log(message): console.write(message)

TimestampLogger implements Logger:
    constructor(inner: Logger, clock: Clock)
    log(message): inner.log("[" + clock.now() + "] " + message)

FilteredLogger implements Logger:
    constructor(inner: Logger, minimumLevel)
    log(message): if shouldLog(message): inner.log(message)

// composed: filtered, then timestamped, then written
logger = new FilteredLogger(new TimestampLogger(new ConsoleLogger(), clock), "WARN")
```

## 3. Delegation

A type hands work to an object it holds, instead of inheriting the behavior.

```
// not: type Stack extends DynamicArray
type Stack:
    private items = new DynamicArray()

    push(item): items.append(item)
    pop():      return items.removeLast()
    peek():     return items.last()
    // Stack does not expose the array's full surface
```

**Benefit:** `Stack` controls its own surface. A caller cannot index into the middle of a stack.
(Examples by language: [examples-by-language.md](examples-by-language.md).)

## 4. Mixins and traits

Compose behavior by mixing small, independent pieces of behavior into a type, where the language
supports it.

```
mixin Serializable:
    serialize(): return toText(self)

mixin Validatable:
    validate(): ...the validation logic...

type User includes Serializable, Validatable, based on BaseModel
```

Prefer a mixin that needs nothing from its host. One that reaches into the host's private state is
inheritance by another name.
(Examples by language: [examples-by-language.md](examples-by-language.md).)

## When inheritance is still appropriate

| Situation | Recommendation |
|-----------|----------------|
| A genuine "is-a" relationship that is stable | inheritance is fine |
| Sharing an implementation across two or three closely related types | inheritance is fine |
| A framework requires it (its base types must be extended) | inheritance is fine |
| Behavior varies along many dimensions | use composition |
| Combining behaviors from several sources | use composition |
| A hierarchy deeper than three levels | refactor to composition |

(Examples by language: [examples-by-language.md](examples-by-language.md).)

## Deciding

1. Is there a genuine, stable "is-a" relationship? Then consider inheritance.
2. Does the child use all of its parent's behavior? If not, use composition.
3. Will you need to combine behaviors in different ways? Use composition.
4. Is the hierarchy deeper than two or three levels? Refactor to composition.
5. Could the base type change in ways that break its children? Use composition.
