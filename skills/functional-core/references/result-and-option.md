# Result and option

## Option (maybe)

A value that may or may not be there.

```
type Option of T = Some(T) | None

Some(42)    // a value
None        // no value
```

### When to use it

- Looking up something that may not exist: a key in a map, a record by its identifier.
- An optional setting or parameter.
- The first or last element of a collection that may be empty.

### Operations

```
option.map(f)              // transform the value, if there is one
option.flatMap(f)          // chain another function that returns an option
option.getOrElse(default)  // unwrap, with a default for None
option.match(some: ..., none: ...)
```

### Example

```
function findUser(id) -> Option of User:
    user = users.lookup(id)
    return user exists ? Some(user) : None

findUser(42)
    .map(user -> user.email)
    .getOrElse("unknown@example.com")
```

## Result (either)

A computation that either succeeds with a value or fails with an error value.

```
type Result of (T, E) = Ok(T) | Err(E)

Ok(42)                       // success
Err("not found")             // failure, with a reason
Err(ValidationError(...))    // failure, with a typed error
```

### When to use it

- Parsing or validation that can fail.
- An outside operation (a network call, a file read) that can fail.
- Any function whose callers need to know **why** it failed.

### Operations

```
result.map(f)           // transform the success value
result.mapErr(f)        // transform the error value
result.flatMap(f)       // chain another function that returns a result
result.match(ok: ..., err: ...)
result.unwrap()         // the value, or a failure raised: only at the boundary
```

### Chaining

```
function processOrder(rawData):
    return parseOrderData(rawData)      // Result of (OrderData, ParseError)
        .flatMap(validateOrder)          // Result of (ValidOrder, ValidationError)
        .flatMap(calculatePricing)       // Result of (PricedOrder, PricingError)
        .map(formatConfirmation)         // Result of (Confirmation, an error)
```

The first failure skips every later step and arrives at the end unchanged.

## Choosing

| Situation | Type | Why |
|-----------|------|-----|
| The value may not exist | option | no reason is needed |
| The operation can fail and the caller needs the reason | result | the reason is kept |
| Several kinds of failure are possible | a result whose error is one of several typed variants | each variant can be handled |
| A simple "may be missing" check | the language's nullable or optional type, or an option | whichever the language makes safe |
| A critical failure of the system | an exception | truly exceptional, and not recoverable |

What each language provides is in
[result-and-option-by-language.md](result-and-option-by-language.md).

## Anti-patterns

### Catch everything, return nothing

```
// avoid: the reason for the failure is lost
try: ...
catch anything: return null
```

### Ignoring the result

```
// avoid: the failure is silently dropped
parseAge(input)          // the result is never looked at
```

### A result inside a try-catch

```
// avoid: mixing the two styles defeats the purpose
try:
    result = parseAge(input)
    if result.isErr(): throw result.error
catch error: ...
```
