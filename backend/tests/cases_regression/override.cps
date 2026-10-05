class A { function f(): integer { return 1; } } class B: A { function f(): string { return "x"; } } let a: A = new B(); print(a.f() + 1);
