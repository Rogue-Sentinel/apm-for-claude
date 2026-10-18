# Dependency inversion: patterns

## 1. Constructor injection

Pass dependencies in through the constructor. This is the most common pattern, and the one to
reach for first.

```
type NotificationService:
    constructor(emailSender: EmailSender, templates: TemplateEngine)

    notify(user, event):
        body = templates.render(event.template, event.data)
        emailSender.send(user.email, body)
```

Testing it needs no framework, only small fakes:

```
sender = new RecordingEmailSender()            // remembers what it was asked to send
templates = new FixedTemplates("Hello")
service = new NotificationService(sender, templates)

service.notify(user, event)
assert sender.sent == [(user.email, "Hello")]
```

## 2. The consumer owns the interface

The interface belongs to the high-level module that uses it, not to the low-level module that
provides it.

```
// domain/ports/OrderRepository        (owned by the domain)
interface OrderRepository:
    save(order)
    findById(id) -> Order

// infrastructure/SqlOrderRepository   (implements the domain's interface)
import domain.ports.OrderRepository
SqlOrderRepository implements OrderRepository: ...
```

**The key point:** the domain never imports from infrastructure. Infrastructure imports from the
domain.

## 3. The composition root

Wire every dependency in one place, at the program's entry point.

```
// main: the composition root
db = new SqlConnection(config)
orders = new SqlOrderRepository(db)
email = new SmtpEmailSender(mailConfig)
placeOrder = new OrderService(orders, email)

server.onPost("/orders", request -> placeOrder.placeOrder(request.body))
```

**The rule:** only the composition root knows the concrete types. Every other module depends on
abstractions.

## 4. A factory function

When the concrete type must be chosen at run time, choose it in a factory, in one place.

```
interface PaymentGateway:
    charge(amount) -> Receipt

function createPaymentGateway(config) -> PaymentGateway:
    if config.provider == "card-provider":   return new CardProviderGateway(config.apiKey)
    if config.provider == "wallet-provider": return new WalletProviderGateway(config.clientId)
    fail "unknown payment provider: " + config.provider
```

## When not to invert

Not every dependency needs an interface in front of it.

| Dependency | Invert? | Why |
|------------|---------|-----|
| The standard library (arithmetic, text) | no | stable; it does not change under you |
| Value types | no | simple, with no side effects |
| Domain entities | no | the same layer, changing at the same rate |
| Infrastructure (database, network, file system) | yes | changes independently of the domain |
| External APIs | yes | unstable, and controlled by someone else |
| Framework code | it depends | on how tightly the code is coupled to it |

## The direction rule

```
Domain  <--  Application  <--  Infrastructure
                  |
          Interfaces (ports)
```

- The domain defines the interfaces (ports).
- Infrastructure implements them (adapters).
- The application wires them together.
- **Every arrow points inward**: infrastructure depends on the domain, never the reverse. The full
  treatment is `apm:clean-architecture`.
