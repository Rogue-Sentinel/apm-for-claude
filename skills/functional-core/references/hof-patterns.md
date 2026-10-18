# Higher-order function patterns

## 1. Transform (map)

Apply one transformation to every element.

```
names = users.map(user -> user.name)
celsius = fahrenheitValues.map(f -> (f - 32) * 5 / 9)
labels = items.map(item -> item.name + ": " + formatMoney(item.price))
```

## 2. Select (filter)

Keep the elements that match a condition.

```
adults = users.filter(user -> user.age >= 18)
errors = logEntries.filter(entry -> entry.level == "error")
inStock = products.filter(product -> product.quantity > 0)
```

## 3. Accumulate (reduce, fold)

Combine all the elements into one value.

```
total = items.reduce((sum, item) -> sum + item.price, 0)

grouped = events.reduce(
    (groups, event) -> groups with event appended under event.type,
    empty map)
```

## 4. Function factory

Return a function configured with specific behavior.

```
function multiplier(factor):
    return value -> value * factor

double = multiplier(2)
triple = multiplier(3)

double(5)   // 10
triple(5)   // 15
```

## 5. Composition

Combine several functions into one. Here, applied right to left:

```
function compose(functions...):
    return x -> functions.reduceRight((value, f) -> f(value), x)

prepareUser = compose(formatForDisplay, validateAge, normalizeEmail)
result = prepareUser(rawUserData)     // normalizeEmail, then validateAge, then formatForDisplay
```

## 6. Middleware and pipelines

Chain functions where each step can change the value, or stop the flow.

```
function pipeline(steps...):
    return input -> steps.reduce((value, step) -> step(value), input)

handleRequest = pipeline(authenticate, authorize, validateInput, execute)
```

When a step can stop the flow, each step returns a result, and the pipeline chains them with
flat-map. The first failure skips every later step and comes out at the end unchanged
([result-and-option.md](result-and-option.md)):

```
function pipeline(steps...):
    return input -> steps.reduce((r, step) -> r.flatMap(step), Ok(input))

handleRequest = pipeline(authenticate, authorize, validateInput, execute)

handleRequest(request)    // Ok(response), or the Err from the first step that failed:
                          // an unauthenticated request never reaches authorize or execute
```

## 7. Partial application

Fill in some arguments now to get a more specific function.

```
function partial(f, presetArguments...):
    return laterArguments... -> f(presetArguments..., laterArguments...)

addTax = partial(multiply, 1.08)
addTax(100)   // 108
```

## Chaining

### Good: a clear pipeline

```
revenue = orders
    .filter(order -> order.status == "completed")
    .map(order -> order.total)
    .reduce((sum, total) -> sum + total, 0)
```

### Bad: everything squeezed into one step

```
revenue = orders.reduce((s, o) -> o.status == "completed" ? s + o.total : s, 0)
```

### Better, when it gets complex: named steps

```
completedOrders = orders.filter(isCompleted)
orderTotals = completedOrders.map(toTotal)
revenue = sum(orderTotals)
```
