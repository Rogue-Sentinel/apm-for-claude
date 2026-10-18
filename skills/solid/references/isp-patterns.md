# Interface segregation: patterns

## 1. Role interfaces

Split one interface into several, each a role that some client plays.

```
// before
interface Document:
    read() -> text
    write(content)
    print()
    fax()

// after
interface Readable:  read() -> text
interface Writable:  write(content)
interface Printable: print()
interface Faxable:   fax()
```

**Benefit:** a read-only document implements only `Readable`; a full document implements all four.

## 2. Composing interfaces

When a client genuinely needs several roles, combine the small interfaces rather than going back
to the fat one.

```
interface ReadWrite extends Readable, Writable

function rewrite(document: ReadWrite):
    content = document.read()
    document.write(transform(content))
```

## 3. Adapting an interface you cannot change

When the fat interface belongs to someone else (a third-party library, a platform), declare the
narrow interface you need and adapt to it.

```
// the library's interface: large, and not yours
interface BigLibraryApi:
    methodA()
    methodB()
    methodC()
    methodD()

// yours: only what you use
interface OnlyWhatINeed:
    methodA()
    methodB()

LibraryAdapter implements OnlyWhatINeed:
    constructor(library: BigLibraryApi)
    methodA(): library.methodA()
    methodB(): library.methodB()
```

The rest of your code depends on `OnlyWhatINeed`, and the library's surface stops at the adapter.
See `apm:clean-architecture` for adapters at the system's edge.

## Sizing guide

| Methods | Assessment | Action |
|---------|------------|--------|
| 1 | possibly too granular | fine for a function-shaped interface (a callback, a predicate) |
| 2 to 5 | ideal | likely well segregated |
| 6 to 10 | review it | check that every client uses every method |
| more than 10 | likely a violation | split by how clients use it |

## Over-segregation

Do not create one interface per method. Keep together the methods that the same client always
uses together. The goal is grouping **by client**, not the smallest method count.

The test: **does every client of this interface call every one of its methods?**

- Yes: the interface is fine.
- No: split it by how its clients use it.
