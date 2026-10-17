# Replace conditional with polymorphism: before and after

## Example 1: payment processing

### Before: a conditional on type

```
function processPayment(payment):
    if payment.type == "credit_card":
        validateCardNumber(payment.cardNumber)
        chargeCard(payment.cardNumber, payment.amount)
        return { status: "charged", fee: payment.amount * 0.029 }
    else if payment.type == "bank_transfer":
        validateRoutingNumber(payment.routingNumber)
        initiateBankTransfer(payment.routingNumber, payment.amount)
        return { status: "pending", fee: 1.50 }
    else if payment.type == "crypto":
        validateWalletAddress(payment.walletAddress)
        sendCryptoPayment(payment.walletAddress, payment.amount)
        return { status: "broadcast", fee: 0 }
```

**The problem:** a new payment type means editing this function, and each branch tangles its own
validation, execution and fee logic together.

### After: polymorphic dispatch

```
interface PaymentProcessor:
    validate(payment)
    execute(payment)
    calculateFee(amount) -> number
    resultStatus() -> text

CreditCardProcessor implements PaymentProcessor:
    validate(payment):     validateCardNumber(payment.cardNumber)
    execute(payment):      chargeCard(payment.cardNumber, payment.amount)
    calculateFee(amount):  return amount * 0.029
    resultStatus():        return "charged"

BankTransferProcessor implements PaymentProcessor:
    validate(payment):     validateRoutingNumber(payment.routingNumber)
    execute(payment):      initiateBankTransfer(payment.routingNumber, payment.amount)
    calculateFee(amount):  return 1.50
    resultStatus():        return "pending"

CryptoProcessor implements PaymentProcessor:
    validate(payment):     validateWalletAddress(payment.walletAddress)
    execute(payment):      sendCryptoPayment(payment.walletAddress, payment.amount)
    calculateFee(amount):  return 0
    resultStatus():        return "broadcast"

function processPayment(payment, processor: PaymentProcessor):
    processor.validate(payment)
    processor.execute(payment)
    return { status: processor.resultStatus(), fee: processor.calculateFee(payment.amount) }
```

---

## Example 2: notification delivery, with a registry as the factory

### Before

```
function sendNotification(user, message):
    switch user.preferredChannel:
        "email": emailClient.send(user.email, message.subject, message.body)
        "sms":   smsGateway.send(user.phone, firstCharacters(message.body, 160))
        "push":  pushService.send(user.deviceToken, message.subject, message.body)
```

### After

```
interface NotificationChannel:
    send(user, message)

EmailChannel implements NotificationChannel:
    send(user, message): emailClient.send(user.email, message.subject, message.body)

SmsChannel implements NotificationChannel:
    send(user, message): smsGateway.send(user.phone, firstCharacters(message.body, 160))

PushChannel implements NotificationChannel:
    send(user, message): pushService.send(user.deviceToken, message.subject, message.body)

// the registry is the factory: the one place a channel is chosen
channels = { "email": EmailChannel(), "sms": SmsChannel(), "push": PushChannel() }

function sendNotification(user, message):
    channels[user.preferredChannel].send(user, message)
```

A new channel is one new implementation and one registry entry; no existing branch is edited.

---

## When not to use polymorphism

- **Two simple branches.** `if isAdmin ... else ...` is fine; classes would be overkill.
- **Pure data mapping.** Use a lookup table: `TAX_RATES = { "US": 0.08, "UK": 0.20 }`.
- **Temporary conditions.** Feature flags and one-off checks that will be removed.
- **Measured hot paths.** Dynamic dispatch adds an indirection; measure before refactoring.

## Decision checklist

1. [ ] Does the conditional branch on a type, status or category?
2. [ ] Does the same branching appear in more than one function?
3. [ ] Are new types likely to be added?
4. [ ] Does each branch hold non-trivial logic (more than a single expression)?

Three or more yeses: polymorphism is the right move. Fewer: leave it, or use a table.

## Pitfalls

- Replacing a trivial conditional.
- Building a hierarchy for a conditional that will never grow.
- Forgetting the factory or registry that picks the implementation, so the switch just moves there
  and multiplies.
- Using polymorphism where a lookup table would do.
- Over-engineering: not every if-else needs it.
