// Constructor heredado y metodo sobrescrito.
class Animal {
  let name: string;
  function constructor(name: string) { this.name = name; }
  function speak(): string { return this.name; }
}
class Dog : Animal {
  let age: integer = 2;
  function speak(): string { return this.name + " ladra"; }
}
let animal: Animal = new Dog("Toby");
print(animal.speak());
