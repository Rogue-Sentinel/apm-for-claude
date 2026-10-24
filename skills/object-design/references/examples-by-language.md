# Examples by language

These are the names the original skills used for the generic wording in the object-design skill.

| Generic wording | Language or ecosystem | Original example |
|-----------------|-----------------------|------------------|
| a string form that leaks the internal structure | Java, JavaScript | `toString()` |
| the full surface of the type a delegate holds | Java | `ArrayList.get(index)`, which a caller cannot call on a `Stack` |
| a mixin | JavaScript | the class-factory mixin, shown below |
| a framework that requires inheritance | JavaScript | React class components |

The class-factory mixin, as the original showed it:

```
const Serializable = (Base) => class extends Base {
  serialize() { return JSON.stringify(this) }
}
```
