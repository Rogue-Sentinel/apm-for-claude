# Result and option, by language

What each language offers for absence (an option) and for an expected failure (a result). Where a
language has nothing built in, a small custom type or a well-known library fills the gap. A project
picks one and uses it everywhere, so a reader meets a single idiom.

| Language | Absence (option) | Failure (result) |
|----------|------------------|------------------|
| Rust | `Option<T>` | `Result<T, E>` |
| Kotlin | `T?` | `Result<T>`, or `Either` from the Arrow library |
| Swift | `Optional<T>`, written `T?` | `Result<Success, Failure>` |
| TypeScript | a custom type, or `Option` from fp-ts | a custom type, or `Either` from fp-ts |
| Java | `Optional<T>` | a custom type, or `Either` from Vavr |
| Scala | `Option[T]` | `Either[E, T]`, or `Try[T]` |
| Go | a `nil` return, or a second `ok` value | the `value, err` pair |
| C++ | `std::optional<T>` | `std::expected<T, E>` (C++23), or a custom type |
| Python | `Optional[T]`, meaning `T` or `None`, with a type checker | a custom result type, or exceptions kept for the truly exceptional |
| C# | nullable reference types, `T?` | a custom result type, or a library |
