# Class scanners by language

`<CLI> metrics` counts the public methods of a class only for the languages that have a class scanner.

## Languages with a class scanner

- **Python.**
- **C++.** A `.h` header counts as C++ when its code declares a class, a namespace, a template or an
  access label. A `.h` header with none of these is read as C, which has no classes to count. A C++
  header with no such marker (for example one holding only a `struct` with methods) is read as C too, and
  its classes are missed (ADR 0004).

## Every other language

For any other language with classes, the review-flag line says "not measured" and names the language.
It never reports 0, because 0 would say the classes were checked and found small.
