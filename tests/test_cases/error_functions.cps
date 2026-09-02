// Test: argumentos, retorno y función duplicada
function add(a: integer, b: integer): integer {
  return "invalid";
}

function add(value: integer): integer {
  return value;
}

let result: integer = add(true);
