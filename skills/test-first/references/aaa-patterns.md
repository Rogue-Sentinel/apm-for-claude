# Arrange, act, assert: patterns

## Pattern 1: a returned value

```
test "calculateDiscount gives 10% on orders over 100":
    // arrange
    order = Order(total: 150.00)

    // act
    discount = calculateDiscount(order)

    // assert
    expect(discount).toBe(15.00)
```

**Why it works:** one behavior, minimal setup, one clear assertion.

---

## Pattern 2: a change of state

```
test "deactivate sets the status to inactive":
    // arrange
    user = User(status: "active")

    // act
    user.deactivate()

    // assert
    expect(user.status).toBe("inactive")
```

**Why it works:** the assertion checks the side effect of the action, the change of state.

---

## Pattern 3: an error

```
test "withdraw fails with InsufficientFunds when the balance is too low":
    // arrange
    account = Account(balance: 50)

    // act and assert
    expect(() -> account.withdraw(100)).toFail(InsufficientFundsError)
```

**Note:** when testing for an error, act and assert may merge. This is the one accepted deviation
from strict separation.

---

## Pattern 4: an interaction

```
test "register sends a welcome email":
    // arrange
    emails = RecordingEmailSender()
    registration = RegistrationService(emails)

    // act
    registration.register("alice@example.com")

    // assert
    expect(emails.sent).toContain(to: "alice@example.com", bodyContaining: "Welcome")
```

**Why it works:** the double records the interaction, and the test checks the part of it that is
the contract (the recipient, a welcome) without coupling to the full wording. Use a recording fake
like this only where sending is slow or external; see
[writing-good-tests.md](writing-good-tests.md).

---

## Pattern 5: table-driven

```
cases = [
    { input: "",        expected: false },
    { input: "abc",     expected: false },
    { input: "a@b",     expected: false },
    { input: "a@b.com", expected: true  },
]

for each { input, expected } in cases:
    test "isValidEmail(" + input + ") is " + expected:
        // arrange: in the table

        // act
        result = isValidEmail(input)

        // assert
        expect(result).toBe(expected)
```

**Why it works:** many scenarios reuse one structure, and every expected value is a literal.

---

## Anti-patterns

### Mixed phases

```
// BAD: setup and assertions interleaved
test "process order":
    item = createItem()
    cart.add(item)
    expect(cart.count()).toBe(1)      // an assertion in the middle
    cart.checkout()
    expect(cart.count()).toBe(0)
```

Split it: one test for adding, one for checking out.

### Excessive arrangement

```
// BAD: most of this setup is irrelevant
test "getName returns the full name":
    user = User(
        name: "Alice Smith",
        email: "alice@example.com",   // irrelevant
        age: 30,                      // irrelevant
        address: "123 Main St",       // irrelevant
        preferences: { theme: "dark" } // irrelevant
    )
    expect(user.getName()).toBe("Alice Smith")
```

Arrange only what the behavior needs; a builder with defaults hides the rest.

### No assert

```
// BAD: runs code, verifies nothing
test "process data":
    data = loadTestData()
    processor.process(data)
    // no assertion
```

A test that cannot fail is not a test.

### Other signs
- Setup copied across many tests: extract a helper or a shared setup.
- Several actions before asserting: several behaviors, so several tests.
- A name that does not describe the scenario.
- No arrange at all because the test leans on hidden global state.
