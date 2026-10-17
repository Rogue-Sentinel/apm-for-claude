# Extraction heuristics

## When to extract

### The comment heuristic
If a comment says what the next block does, the comment is the function's name. Delete the comment
and replace the block with a call.

### The indent heuristic
The body of an `if`, `for`, `while` or `try` is a candidate, especially when it runs past 5 lines.
Three or more levels of nesting almost always hide a function.

### The reuse heuristic
If the same logic appears in two or more places, extract it. Small variations can often be unified
with a parameter.

### The abstraction-level heuristic
When a function mixes orchestration (`processOrder`) with detail
(`total = total + item.price * item.quantity`), extract the detail so the parent reads at one level
of abstraction.

### The testability heuristic
If a behavior you want to test is buried inside a larger function, extract it so it can be tested
on its own.

## Naming the extracted function

| Bad name | Good name | Why |
|----------|-----------|-----|
| `doStuff` | `validateInput` | describes the purpose |
| `helper` | `formatCurrency` | describes the result |
| `process` | `applyDiscount` | names the action |
| `handle` | `retryWithBackoff` | reveals the strategy |

### Naming rules
1. A verb or verb phrase.
2. Name the **what**, not the **how**.
3. If the name needs "and", the function does too much: split it.
4. If you cannot name it, you do not yet understand what it does.

## Parameters

| Count | Verdict |
|-------|---------|
| 0 | ideal: it works on its own object's state |
| 1 to 2 | good: clear inputs |
| 3 | acceptable: consider a parameter object |
| 4 or more | too many: decompose further |

## The extraction checklist

1. [ ] Find the block's boundaries.
2. [ ] List every variable the block reads (its inputs).
3. [ ] List every variable the block writes (its outputs).
4. [ ] Choose a name that reveals the intent.
5. [ ] Create the function, inputs as parameters and output as the return value.
6. [ ] Move the block into it.
7. [ ] Replace the original block with a call.
8. [ ] Run the tests.
9. [ ] Check that the parent now reads at one level of abstraction.

## Pitfalls

- The extracted function still needs many parameters: decompose further.
- It is named after its mechanism (`loopOverItems`), not its purpose (`calculateTotal`).
- It is too small to add clarity: a one-liner nobody needed named.
- Scope was broken: a variable the block wrote is no longer seen by the caller.
- It went into another type when it should have stayed local.
