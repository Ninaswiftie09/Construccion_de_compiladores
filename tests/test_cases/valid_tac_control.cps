// Ciclos, ramas y seleccion.
let total = 0;
for (let i = 0; i < 5; i = i + 1) {
  if (i == 2) { continue; }
  total = total + i;
}
while (total < 12) { total = total + 1; }
do { total = total - 1; } while (total > 10);
switch (total) {
  case 10: print("diez"); break;
  default: print("otro");
}
