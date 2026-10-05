# Compiscript TAC v1

## Objetivo y alcance

La representación intermedia traduce Compiscript a código de tres direcciones.
No interpreta el programa, no imprime resultados de sus `print`, no genera
assembler y no produce código objeto. Los temporales contienen valores simbólicos
durante la traducción, no resultados calculados.

ANTLR 4.13.2 genera el lexer, parser y visitor base desde `Compiscript.g4`.
El visitor semántico valida el árbol y conserva los símbolos resueltos y sus
alcances. Si existe cualquier error léxico, sintáctico o semántico, la salida
`intermediateCode` es `null` y no se crea ningún archivo de TAC para ese análisis.

## Forma y operandos

Cada instrucción JSON tiene `index`, `op`, `arg1`, `arg2`, `result` y `handler`.
Los operandos ausentes son `null`. `handler` identifica el catch activo en
operaciones que puedan fallar; también ayuda a dibujar aristas de excepción.
El campo `text` contiene una forma legible de las mismas instrucciones.

- Literales: `12`, `2.5`, `"texto"`, `true`, `false`, `null`.
- Variables: `s1.x`, `s3.x`. La identidad del alcance evita colisiones de nombres.
- Temporales: `t1`, `t2`, etc., locales a cada registro de activación.
- Etiquetas de salto: `L1`, `L2`, únicas en el programa.
- Etiquetas de función/clase: dirección simbólica del símbolo, como `s1.sum`.
- Destinos compuestos: `t1[t2]`, `t1.name`, `this.name`.

Los accesos compuestos son modos de direccionamiento de la IR. `copy` escribe
el valor en el destino: un slot, campo o elemento de arreglo. No agrega un
operador aritmético escondido. La IR conserva nombres de campos e índices;
una fase futura podría bajar estos modos a offsets y operaciones de memoria.

## Instrucciones

| Operación | Forma legible | Significado |
| --- | --- | --- |
| `declare` | `s1.x = declare integer` | Reserva un slot sin valor inicial. |
| `const` | `s1.x = const 3` | Inicializa un símbolo ya validado como constante. |
| `copy` | `destino = valor` | Copia un valor a un slot, campo o índice. |
| `+ - * / %` | `t3 = t1 + t2` | Operación aritmética; `+` admite concatenación según los tipos. |
| `< <= > >= == !=` | `t3 = t1 < t2` | Comparación que produce boolean. |
| `neg`, `not` | `t2 = neg t1` | Menos unario o negación lógica. |
| `label` | `L1:` | Destino de control de flujo. |
| `goto` | `goto L1` | Salto incondicional. |
| `if_true`, `if_false` | `if_false t1 goto L2` | Salta según un boolean. |
| `array` | `t1 = array 3` | Reserva un arreglo con tres elementos. |
| `load_index` | `t2 = load_index t1, 0` | Lee un elemento; debe comprobar rango en una ejecución futura. |
| `length` | `t2 = length t1` | Obtiene la cantidad de elementos. |
| `closure` | `t1 = closure s1.f, s1` | Par de etiqueta y entorno léxico de la función. |
| `param` | `param t1` | Agrega un argumento a la llamada siguiente. |
| `receive` | `s2.a = receive 0` | Copia el argumento cero al parámetro del frame llamado. |
| `call` | `t2 = call t1, 2` | Llama a un cierre con dos argumentos y recoge el retorno. |
| `return` | `return t1` | Devuelve un valor; sin operando representa un retorno vacío. |
| `begin`, `end` | `begin s2` | Delimita una región y su frame. |
| `print` | `print t1` | Representa la operación de salida; no la ejecuta. |
| `class` | `s1.B = class s1.A` | Declara un descriptor de clase y su clase base. |
| `method` | `s1.B = method f, s4.f` | Registra un método en el descriptor de clase. |
| `new` | `t1 = new s1.B` | Reserva un objeto con el layout de B. |
| `init_object` | `init_object t1, s1.B` | Llama al inicializador de campos `s1.B.init` con receptor t1. |
| `member` | `t2 = member t1, f` | Lee un campo o produce un método ligado al objeto. |
| `bind` | `t2 = bind t1, constructor` | Produce un cierre de método con receptor y despacho dinámico. |
| `try_begin` | `try_begin catch L1` | Apila el manejador de excepción. |
| `try_end` | `try_end` | Retira el manejador más reciente. |
| `catch` | `s4.error = catch` | Copia la excepción al símbolo local del catch. |

Las firmas, descriptores de clase, layouts y etiquetas son metadatos declarativos.
Un consumidor futuro debe registrarlos antes de traducir llamadas, incluso si
la declaración aparece después de la llamada. Los cuerpos tienen un salto de
salida para que el flujo normal no entre en una función o inicializador.

## Expresiones y orden de evaluación

Se respeta la precedencia que establece ANTLR y se evalúa de izquierda a derecha.
Las expresiones binarias guardan el operando izquierdo si una expresión posterior
podría cambiar la variable. Por ejemplo, `x + (x = 5)` usa el valor anterior de x
para la suma. Los índices y receptores de asignación también se conservan antes
de evaluar el lado derecho.

Compiscript:

```cps
let x = (2 + 3) * (4 + 5);
```

TAC de las operaciones:

```text
s1.x = declare integer
t1 = 2 + 3
t2 = 4 + 5
t3 = t1 * t2
s1.x = t3
```

No hay plegado de constantes: se conservan las operaciones en vez de sustituirlas
por el resultado numérico. `/` y `%` siguen las reglas de tipo del analizador;
una ejecución futura debe definir el resultado numérico y la excepción por cero.

`&&` y `||` generan saltos de cortocircuito. En `false && f()`, el salto se emite
antes de la llamada y llega a una etiqueta situada después de ella. El ternario
asigna a un temporal reservado desde dos ramas, y solo una rama se ejecutaría.

## Temporales: asignación y reciclaje

`TemporaryPool` mantiene un conjunto `live` y una pila `free`. Al pedir un temporal,
primero extrae uno libre; solo crea otro cuando no hay libres. Al consumir el
último uso del valor, lo retira de `live` y lo devuelve a `free`. Liberar dos veces
un valor no agrega dos copias a la pila.

Los operandos de una operación se liberan después de emitirla. El destino queda
vivo hasta que lo consuma la operación siguiente. Para el ejemplo anterior,
t1 y t2 se liberan tras la multiplicación; t3 se libera tras copiarlo a x.
La expresión siguiente puede usar esos mismos nombres.

El resultado de un ternario permanece reservado al traducir ambas ramas.
En `foreach`, colección, índice, longitud y comparación no se reciclan durante
el cuerpo. Los argumentos permanecen vivos hasta emitir su llamada. Cada función
usa un pool independiente: los temporales del caller y callee pertenecen a
distintas activaciones, incluso en recursión.

La salida informa `created`, `reused` y `peakLive` por frame. Es reciclaje local
durante la traducción, no un asignador global de registros físicos ni un algoritmo
de optimización de todo el CFG.

## Control de flujo

- `if/else`: salto condicional a la rama alternativa y salto al final común.
- `while`: condición antes del cuerpo; `continue` llega al paso que vuelve a ella.
- `do/while`: cuerpo antes de la condición; `continue` llega a la condición.
- `for`: inicialización una vez, condición opcional, cuerpo, actualización opcional.
  La posición de los puntos y coma distingue condición y actualización omitidas.
- `foreach`: toma una referencia al arreglo una vez, longitud, índice desde cero,
  comparación, carga del elemento y aumento del índice.
- `switch`: evalúa el selector una vez, compara cases en orden, salta al case
  correspondiente o al default. Los cuerpos permiten caída al case siguiente;
  `break` llega al final del switch. `continue` busca el ciclo exterior.
- `break/continue`: usan una pila de destinos y no atraviesan funciones.

Los cases usan los tipos escalares admitidos por el lenguaje y deben ser
compatibles con el selector. Esta segunda parte admite el switch numérico de
los ejemplos entregados, además de boolean y string.

## Funciones, argumentos, recursión y cierres

La tabla contiene las firmas antes del recorrido de cuerpos. Una llamada crea
un cierre con la etiqueta del símbolo y la identidad de su entorno léxico.
Se evalúan **todos** los argumentos en orden antes de emitir los `param` de
esa llamada. Así `f(1, f(2, 3))` termina la llamada interna antes de preparar
los dos argumentos externos.

El callee recibe sus argumentos por índice; su `return` produce el valor de
`call`. Las funciones sin retorno explícito tienen un retorno vacío al final.
En funciones con retorno garantizado puede quedar un retorno vacío inalcanzable:
no se realiza eliminación de código muerto.

Un cierre anidado conserva el entorno donde se declaró su función. Las
referencias capturadas tienen direcciones simbólicas del frame exterior y un
consumidor futuro debe resolverlas mediante el enlace estático. Las llamadas
recursivas crean activaciones independientes; no sobreescriben los slots o
temporales de la llamada anterior. Solo se describe ese contrato, no se ejecuta.

## Registros de activación y símbolos

`Symbol.storage` conserva dirección, tipo de almacenamiento, etiqueta o offset
y frame. `Scope.activationRecord` guarda el registro y sus slots. `prepare_layout`
trabaja sobre la misma tabla que construyó la fase semántica.

Se usa una máquina abstracta con celdas alineadas de ocho bytes. Boolean, entero,
float y referencias ocupan una celda. Arreglos, strings y objetos usan referencias;
sus datos no se almacenan dentro del slot. No es un ABI real ni memoria asignada
por Python al programa fuente.

| Offset | Contenido reservado |
| --- | --- |
| 0 | Dirección de retorno |
| 8 | Enlace dinámico: caller |
| 16 | Enlace estático: entorno léxico |
| 24 | Receptor `this`, cuando corresponde |
| 32 en adelante | Parámetros y variables locales |
| `temporaryOffset` | Celdas de temporales creados por el pool |

El tamaño del frame incluye cabecera, parámetros, variables de todos sus bloques
y temporales. Los bloques no crean activaciones separadas; crean nombres de
almacenamiento distintos dentro de la activación de su función. El registro
global representa el almacenamiento del programa. El registro de clase es una
plantilla de entorno e inicialización, no un objeto construido durante el análisis.

## Clases, objetos y herencia

La salida `classes` contiene el descriptor, clase base, campos y tabla de métodos.
Un objeto reserva ocho bytes para su descriptor y una celda por campo. Los campos
heredados mantienen offsets; los nuevos se agregan al final. Un método sobrescrito
reemplaza su etiqueta en la tabla de métodos de la clase derivada.

`new` reserva simbólicamente el objeto; `init_object` inicializa los campos de la
base antes que los propios. Después se liga y llama el constructor, que puede
ser heredado. El inicializador generado tiene etiqueta `<clase>.init` y usa `this`.
Un acceso a método obtiene un cierre con receptor, resuelto con la clase dinámica
del objeto; por ello una referencia de tipo base conserva el método sobrescrito.

Los layouts incluyen `size`, `fields`, `methods` y `classDescriptor`. Los campos
también llevan `objectOffset` en la tabla de símbolos. Las etiquetas conservan
identidades de alcance para distinguir clases con igual nombre.

## Try/catch

`try_begin` instala un manejador y el cuerpo se traduce con ese manejador activo.
La salida normal emite `try_end` y salta sobre el catch. Si una operación falla,
un consumidor futuro salta al catch más cercano, retira su manejador y entrega
la excepción a `catch`. Una excepción dentro de un catch usa el manejador exterior.

`return`, `break` y `continue` retiran los manejadores que abandonan antes de
saltar. Las funciones anidadas comienzan con su propia pila de manejadores: una
declaración de función dentro de un try no hereda el catch de quien la declaró.
Las excepciones de una llamada se propagan al caller y su catch activo.

La gramática no incluye `throw` ni `finally`. Se representan fallos futuros de
operaciones, como un índice dinámico fuera de rango. Un error estático conocido,
como `a[10]` sobre un arreglo literal corto, bloquea TAC aunque esté dentro de try.

## Salidas, diagramas y validación

La API guarda SVG, PNG y DOT del árbol, símbolos y CFG en una carpeta única por
análisis. El CFG divide la secuencia en bloques básicos y conecta etiquetas,
ramas, continuación y manejadores. Los cuerpos de funciones son regiones propias;
las llamadas se representan como instrucciones, no como aristas de un grafo de llamadas.

`program.tac` guarda el texto; `program.json` guarda cuádruplas, frames, layouts y
estadísticas. Los archivos generados son locales y se excluyen de Git.

Las pruebas de `test_tac.py` verifican operadores, saltos resueltos, precedencia,
efectos, cortocircuito, llamadas anidadas, ocultamiento, offsets, herencia y reciclaje.
`test_diagrams.py` valida PNG/SVG, persistencia, acceso por API y bloqueo de archivos
TAC ante errores. `App.test.tsx` comprueba apertura de archivos, previsualización,
zoom, diagnósticos y descarte de resultados anteriores al editar.
