// Test: clases, constructor, herencia y arreglos
class Animal {
  let name: string;

  function constructor(name: string) {
    this.name = name;
  }

  function label(): string {
    return this.name;
  }
}

class Dog : Animal {
  function description(): string {
    return this.name + " dog";
  }
}

let dog: Animal = new Dog("Luna");
let scores: integer[] = [90, 95, 100];
foreach (score in scores) {
  print(score);
}
