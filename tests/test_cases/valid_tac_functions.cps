// Recursion, captura y llamadas anidadas.
function factorial(n: integer): integer {
  if (n <= 1) { return 1; }
  return n * factorial(n - 1);
}
function add(a: integer, b: integer): integer { return a + b; }
function outer(seed: integer): integer {
  function inner(): integer { return seed + 1; }
  return inner();
}
print(add(factorial(4), outer(2)));
