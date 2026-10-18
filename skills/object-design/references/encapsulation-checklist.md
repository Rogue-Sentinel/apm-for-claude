# Encapsulation checklist

## Fields

- [ ] Is every field private (or, where the language has it, protected with a stated reason)?
- [ ] Does every setter that remains validate its input and enforce the invariants?
- [ ] Are mutable collections copied, or wrapped in a read-only view, before they are returned?
- [ ] Can any outside caller put the object into an invalid state?

## Behavior

- [ ] Does the type expose behavior (methods that do something) rather than just data (getters)?
- [ ] Is the decision-making inside the type, not scattered across its callers?
- [ ] Do method names describe actions, not data access? (`withdraw`, not `setBalance`.)
- [ ] Does the type enforce its own business rules?

## Smells that encapsulation fixes

| Smell | Fix |
|-------|-----|
| Feature envy | move the logic into the type that owns the data |
| Anemic domain model | add behavior methods; remove getters where possible |
| Data clump | bundle the fields that travel together into a value type |
| Inappropriate intimacy | shrink the public surface and hide the details |
| Message chains | give the first object a method that hides the chain |

The full catalog of these smells is in `apm:code-smells`.

## Tell, don't ask

Instead of asking an object for its data and acting on it, tell the object what to do.

| Ask (avoid) | Tell (prefer) |
|-------------|---------------|
| `if user.getAge() >= 18: grant(user)` | `user.grantIfEligible()` |
| `order.getItems().add(item)` | `order.addItem(item)` |
| `if light.isOn(): light.setOn(false)` | `light.toggle()` |

## When a getter is fine

- A value type that is inherently data: a point, an amount of money, a color.
- A data-transfer type at the system's edge, for serialization or a response.
- A read-only view of state, for display.
- A framework requirement, such as a persistence mapper or a serialization library.

Even then, **prefer a named query to a generic getter**: `account.availableBalance()` over
`account.getBalance()`.
