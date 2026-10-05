// Cortocircuito, precedencia y temporales.
function check(): boolean { return true; }
let enabled = false && check() || !false;
const base = (2 + 3) * (4 + 5);
let result = enabled ? base + 1 : base - 1;
print(result);
