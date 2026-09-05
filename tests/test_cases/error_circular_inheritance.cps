// La herencia circular debe reportarse sin dejar el analizador en un ciclo.
class A : B {}
class B : A {}
class C {}
let value: C = new A();
print(missing);
