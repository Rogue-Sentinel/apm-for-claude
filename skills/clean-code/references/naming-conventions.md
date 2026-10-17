# Naming conventions

## General rules

1. **Reveal intent.** The name answers *why* it exists, *what* it does and *how* it is used.
2. **Avoid disinformation.** Do not call something `accountList` if it is not a list; do not use
   `hp` for a hypotenuse.
3. **Make meaningful distinctions.** `productInfo` beside `productData` is noise: pick one term and
   use it everywhere.
4. **Use pronounceable names.** `genymdhms` becomes `generationTimestamp`.
5. **Use searchable names.** A bare `7` cannot be searched for; `MAX_RETRY_COUNT = 7` can.
6. **Avoid mental mapping.** A reader should not have to translate `r` into "the lower-cased URL
   with the host removed".

## By kind of identifier

### Variables and constants
- Nouns or noun phrases.
- Booleans read as predicates: `is`, `has`, `can`, `should` (`isActive`, `hasPermission`,
  `canEdit`).
- Constants follow the language's constant convention, commonly upper snake case:
  `MAX_CONNECTIONS`, `DEFAULT_TIMEOUT_MS`.
- Collections are plural: `users`, `orderItems`, `errorMessages`.
- Units go in the name when the type does not carry them: `timeoutMs`, `altitudeFeet`.

### Functions and methods
- Verbs or verb phrases: `calculateTotal`, `sendEmail`, `validateInput`.
- Accessors: `getBalance`, or just `balance`, following the language's convention.
- Predicates: `isValid`, `hasAccess`, `canProceed`.
- Converters: `toJson`, `fromString`, `asArray`.
- Factories: `createUser`, `buildQuery`, `of`, `from`.

### Types
- Nouns: `User`, `OrderRepository`, `PaymentGateway`.
- Avoid generic suffixes: `Manager`, `Handler`, `Processor`, `Helper`, `Utils`.
- Prefer a name for the role: `ShippingCalculator`, not `ShippingHelper`.
- Interfaces carry no marker prefix: `Repository`, not `IRepository`.

### Packages and modules
- Lower-case, domain-aligned names: `billing`, `authentication`, `shipping`.
- Group by feature, not by technical kind: `orders/`, not `controllers/`, `services/`, `models/`.

## Consistency

Pick one verb per concept and use it everywhere.

| Concept | Choose one | Not a mix of |
|---------|-----------|--------------|
| Read data | `get` | `fetch` / `retrieve` / `find` |
| Make an instance | `create` | `make` / `build` / `new` |
| Remove data | `delete` | `remove` / `destroy` / `purge` |
| Change data | `update` | `edit` / `modify` / `change` |

## Domain language

Use the words the business uses. If the business says "policy", do not call it "rule"; if it says
"claim", do not call it "request". A domain expert should be able to read the code.

## Pitfalls

- Names so long they stop being read (`theListOfAllActiveUserEmailAddresses`): find the right length.
- Renaming without updating every reference: use the editor's rename refactoring.
- Synonyms for one operation (`fetch`, `get`, `retrieve`).
- Type information in names (`userArray`, `nameStr`): the type system already says it.
- Leaving test code on the old names, so the tests become confusing.
