# Purity rules

## The two rules

### 1. Deterministic

The same inputs give the same output. Always, every time.

Pure:

```
function add(a, b): return a + b
function fullName(first, last): return first + " " + last
```

Impure, because the result is not determined by the inputs:

```
function timestamp(): return clock.systemNow()
function newId(): return randomText(36)
function readConfig(): return environment["CONFIG"]
```

### 2. No side effects

The function changes nothing outside its own scope. Side effects include:

- modifying a global or outside variable;
- modifying an input parameter;
- writing to a database, a file or the network;
- logging to the console;
- throwing an exception;
- reading mutable outside state.

## The purity test

Replace the call with its return value. Does the program behave exactly the same?

```
x = add(2, 3)        // -> x = 5           same program: pure
y = saveUser(u)      // -> y = { id: 1 }   the user was never saved: impure
```

## Immutable updates

### Objects

```
// mutating (avoid)
user.name = "Alice"

// immutable (prefer): a new value, the old one untouched
updatedUser = copy of user with name = "Alice"
```

### Lists

```
// mutating (avoid)
items.append(newItem)
items.sortInPlace()

// immutable (prefer)
newItems = items + [newItem]
sortedItems = sorted(items)
```

### Nested values

```
// mutating (avoid)
order.customer.address.city = "Berlin"

// immutable (prefer): rebuild the path to the change, share everything else
updated = copy of order with
    customer = copy of order.customer with
        address = copy of order.customer.address with city = "Berlin"
```

## The pure core and the impure shell

```
// the pure core: all the business logic
function price(items, taxRate, discountRules):
    subtotal = sum of (item.price * item.quantity) for item in items
    discount = applyDiscountRules(subtotal, discountRules)
    tax = (subtotal - discount) * taxRate
    return { subtotal, discount, tax, total: subtotal - discount + tax }

// the impure shell: input and output at the edges
function handleCheckout(cartId):
    items = database.cartItems(cartId)              // impure: a read
    taxRate = taxService.rate(region)               // impure: a network call
    discountRules = database.discountRules()        // impure: a read

    result = price(items, taxRate, discountRules)   // PURE

    database.saveOrder(cartId, result)              // impure: a write
    emailService.sendReceipt(result)                // impure: an email
```

The core gets its tests with plain values and no mocks. The shell has almost no logic left to
test, and its few tests use fakes at the edges (`apm:clean-architecture`).

## Impure operations and their pure alternatives

| Impure | Pure alternative |
|--------|------------------|
| reading the clock | take the time as a parameter |
| drawing a random number | take a seed, or the drawn value, as a parameter |
| writing a log line | return the messages as data, and let the shell write them |
| throwing for an expected failure | return a result (see [result-and-option.md](result-and-option.md)) |
| appending to a list in place | return a new list with the item added |
| setting a field | return a copy with the field changed |
