// El indice dinamico puede fallar en una ejecucion futura.
let values = [1, 2];
let index: integer = 4;
try {
  print(values[index]);
} catch (error) {
  print(error);
}
