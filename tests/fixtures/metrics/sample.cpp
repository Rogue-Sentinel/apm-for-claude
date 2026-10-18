class A {
public:
  void f() const {
    x();
  }
};

A::A() : x_(1) {
  y();
}
