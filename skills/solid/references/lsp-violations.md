# Liskov substitution: violations and fixes

## 1. A strengthened precondition

### Violation

```
type Collection:
    add(item): items.append(item)                 // accepts any item

type UniqueCollection extends Collection:
    add(item):
        if items.contains(item): fail "duplicate" // rejects what the parent accepts
        super.add(item)
```

**The problem:** `UniqueCollection` refuses input that `Collection` accepts, so code written
against `Collection` breaks when handed one.

### Fix

Use composition, not inheritance: a unique collection is its own type and makes no promise to be a
`Collection`.

```
type UniqueCollection:
    items = new Set()
    add(item): items.add(item)
```

## 2. A weakened postcondition

### Violation

```
type Repository:
    findById(id)    // always returns the entity, or fails with NotFound

type CachedRepository extends Repository:
    findById(id): return cache[id] or nothing     // returns nothing instead of failing
```

**The problem:** callers were promised an entity or a NotFound failure, and get neither.

### Fix

Keep the contract: fall back to the parent.

```
type CachedRepository extends Repository:
    findById(id):
        if cache.has(id): return cache[id]
        return super.findById(id)
```

## 3. A broken invariant

### Violation

```
type Rectangle:
    setWidth(w):  width = w
    setHeight(h): height = h
    area(): return width * height

type Square extends Rectangle:
    setWidth(w):  width = w; height = w   // a hidden side effect
    setHeight(h): width = h; height = h   // a hidden side effect
```

**The problem:** a `Rectangle` lets width and height vary independently. `Square` couples them, so
code that sets the width and then the height gets the wrong area.

### Fix

Separate types, with no inheritance between them, or a shared interface that promises only what
both keep.

```
type Rectangle: constructor(width, height)
type Square:    constructor(side)

interface Shape:
    area() -> number     // both implement this, and nothing more
```

## 4. A new failure

### Violation

```
type FileStorage:
    save(data): writeToFile(data)

type ReadOnlyStorage extends FileStorage:
    save(data): fail "read-only storage"
```

**The problem:** callers of `FileStorage.save` were never told it can fail like this.

### Fix

Split the promise, so a read-only store never makes one it cannot keep.

```
interface ReadableStorage:
    read(key) -> data
interface WritableStorage extends ReadableStorage:
    save(data)

FileStorage implements WritableStorage
ReadOnlyStorage implements ReadableStorage    // never promises save()
```

## The substitution test

For every subtype `S` of a base type `T`, one contract test must pass unchanged:

```
function checkContract(instance: T):
    call every public method of T with valid inputs
    assert that each postcondition holds
    assert that every invariant is preserved

// the same test, run against every implementation, fakes included
checkContract(new ConcreteT())
checkContract(new SubtypeS())
checkContract(new SubtypeR())
checkContract(new FakeT())
```

If any subtype fails it, that subtype violates the substitution rule.
