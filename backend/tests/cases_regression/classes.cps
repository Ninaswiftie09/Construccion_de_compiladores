class A { let x: integer = 1; function get(): integer { return this.x; } } class B: A { function f(): integer { return this.x; } } let b = new B(); print(b.get());
