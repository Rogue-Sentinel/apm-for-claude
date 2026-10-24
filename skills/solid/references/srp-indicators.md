# Single responsibility: indicators

## Quick assessment

Answer these about the type:

1. Can you say what it does in one sentence without the word "and"?
2. Does every method use the same core set of the type's fields?
3. Would one stakeholder ask for every change to it?
4. Can you test each method without setting up dependencies unrelated to it?

**Any "no" means the type probably has more than one responsibility.**

## Red flags

### In the name

- A vague, catch-all role: `Manager`, `Handler`, `Processor`, `Service`.
- "And" in the name: `ReaderAndWriter`, `ValidatorAndFormatter`.
- A name too broad to mean anything: `UserHelper`, `DataUtils`, `ApplicationService`.

### In the structure

- A file over the file limit (default 200 lines of logic; see `apm:clean-code`).
- A type at or over the public-method limit (default 7; see `apm:object-design`).
- A single type of about 200 lines, even in a file under the file limit (judged by the reviewer, not measured).
- More than five dependencies passed to its constructor.
- Methods that fall into clusters which never call each other or share fields.
- Private helpers each used by only one public method: each cluster is a candidate for extraction.

### In how it changes

- A one-line change in one method breaks a test for another.
- Two people need to edit the same file for two different features.
- Fixing a bug in feature A requires understanding feature B's code.

## Common responsibilities to separate

| Responsibility | Examples |
|----------------|----------|
| Business rules | validation, calculation, policy enforcement |
| Persistence | save, load, query, cache |
| Presentation | format, render, serialize |
| Communication | send an email, publish an event, call an API |
| Orchestration | coordinate a workflow across services |
| Configuration | read settings, apply defaults |

## Splitting strategies

### Extract a type

Move a group of related methods, and the data they use, into a new type. The original delegates
to it.

```
// before: Invoice formats itself
type Invoice:
    lines, customer
    total()
    toPrintableText()        // presentation mixed into the business type
    toEmailBody()

// after
type Invoice:
    lines, customer
    total()
type InvoiceFormatter:
    toPrintableText(invoice)
    toEmailBody(invoice)
```

### Extract an interface

Declare an interface for the responsibility, then move the implementation into a new type behind
it. That also opens the way to dependency inversion.

```
interface InvoiceSender:
    send(invoice)
EmailInvoiceSender implements InvoiceSender:
    send(invoice): ...
```

### Split by layer

Cut along the architecture's layers: domain logic, application services, infrastructure adapters.
See `apm:clean-architecture`.
