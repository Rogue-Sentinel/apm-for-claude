# Ports and adapters: anatomy

## The model

```
              [ driving adapter ]      an HTTP controller, a command, a screen
                       |
              [ driving port ]         a use case the system offers
                       |
              +-----------------+
              |   domain core   |
              +-----------------+
                       |
              [ driven port ]          something the domain needs
                       |
              [ driven adapter ]       a SQL repository, an email sender, a clock
```

## Ports

### Driving ports (inbound, primary)

What the system can do, as use-case interfaces.

| Port | What it does |
|------|--------------|
| `PlaceOrder` | accept and validate a new order |
| `RegisterUser` | create a user account |
| `GenerateReport` | produce a report for a date range |

### Driven ports (outbound, secondary)

What the system needs from the outside world, as repository and gateway interfaces.

| Port | What it does |
|------|--------------|
| `OrderRepository` | store and retrieve orders |
| `PaymentGateway` | charge a payment method |
| `EmailSender` | send transactional email |
| `Clock` | tell the current time, so tests can set it |

## Adapters

### Driving adapters (inbound)

Translate outside input into calls on the domain.

| Adapter | Technology | Drives |
|---------|------------|--------|
| `OrderHttpController` | a web framework | `PlaceOrder` |
| `OrderCliCommand` | a command-line argument parser | `PlaceOrder` |
| `OrderMessageConsumer` | a message broker or queue | `PlaceOrder` |

### Driven adapters (outbound)

Implement the domain's ports with a specific technology.

| Adapter | Technology | Implements |
|---------|------------|------------|
| `SqlOrderRepository` | a relational database | `OrderRepository` |
| `InMemoryOrderRepository` | a list or a map | `OrderRepository` |
| `ProviderPaymentGateway` | a payment provider's client library | `PaymentGateway` |
| `SmtpEmailSender` | a mail-sending library | `EmailSender` |
| `SystemClock` / `FixedClock` | the operating system's clock / a value set by the test | `Clock` |

(Examples by language: [examples-by-language.md](examples-by-language.md).)

## A directory layout

```
src/
  domain/
    model/
      Order
      Customer
      Money
    ports/
      inbound/
        PlaceOrder
        CancelOrder
      outbound/
        OrderRepository
        PaymentGateway
        EmailSender
    services/
      PlaceOrderUseCase
  adapters/
    inbound/
      http/
        OrderController
      cli/
        OrderCommand
    outbound/
      persistence/
        SqlOrderRepository
        InMemoryOrderRepository
      payment/
        ProviderPaymentGateway
      email/
        SmtpEmailSender
  main                        <- the composition root
```

The names of the directories matter less than the rule they make visible: nothing under `domain/`
imports anything under `adapters/`. The profile's layer map (`standard.layers`) records the
project's own layout, so the reviewer can check it.

## Dependency rules

1. **The domain imports nothing** from adapters or frameworks.
2. **Adapters import from the domain**: the port interfaces and the domain model.
3. **The composition root imports everything** and wires it together.
4. **Port interfaces live in the domain.** The domain owns them, not the adapters.
5. **Use cases may live in the domain** (as `services/` does above) **or in an application layer
   of their own**, between the domain and the adapters. Either works; the profile's layer map
   (`standard.layers`) records which this project chose, so the reviewer checks the right
   direction.

## Testing strategy

| Layer | Test | Dependencies |
|-------|------|--------------|
| Domain | unit tests | none: pure logic |
| Use cases | unit tests | in-memory adapters |
| Adapters | integration tests | the real infrastructure |
| The whole system | end-to-end tests | everything |
