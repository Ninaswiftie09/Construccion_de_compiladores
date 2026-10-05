# Arquitectura

## Alcance

El proyecto implementa análisis estático y generación de TAC para Compiscript.
La salida contiene diagnósticos, tokens, árbol sintáctico, tabla de símbolos,
registros de activación y código intermedio. No existe ejecución ni código objeto.

## Flujo de análisis

```text
código .cps
   |
   +-- Lexer ANTLR ------- tokens + errores léxicos
   |
   +-- Parser ANTLR ------ árbol + errores sintácticos
   |
   +-- Visitor semántico - errores + tabla de símbolos
                              |
                              +-- Si no hay errores: layout y visitor TAC
                              |
                              +-- Graphviz: SVG y PNG guardados
                              |
                              +-- API FastAPI -- IDE React
```

`Compiler` coordina las fases y conserva el árbol recuperado aunque el parser encuentre errores. Esto permite continuar con validaciones semánticas útiles cuando la estructura restante todavía es recorrible.

## Componentes

### Gramática ANTLR

`backend/grammar/Compiscript.g4` define lexer y parser. Los archivos Python generados se reconstruyen con `generate_parser.bat` o `generate_parser.sh` y no se guardan en Git.

ANTLR aplica recuperación por defecto en el parser. El lexer descarta el carácter inválido y continúa. Los listeners personalizados acumulan diagnósticos y eliminan duplicados exactos.

### Analizador semántico

`backend/analyzer/semantic.py` implementa un visitor. Antes de recorrer un alcance registra sus funciones y clases; así una función puede llamarse a sí misma y las declaraciones anidadas pueden capturar símbolos de alcances externos.

Reglas cubiertas:

- operaciones aritméticas, lógicas y comparaciones;
- inferencia básica y compatibilidad en asignaciones;
- constantes y prohibición de reasignación;
- identificadores duplicados o no declarados;
- cantidad y tipo de argumentos, recursión y retornos;
- condiciones booleanas y ubicación de sentencias de control;
- arreglos homogéneos e índices enteros;
- clases, herencia, `this`, miembros y constructores;
- detección directa de instrucciones posteriores a una salida.

El tipo `unknown` evita diagnósticos derivados cuando un error anterior impide conocer un tipo.

Las funciones se distinguen de sus valores de retorno y las clases conservan una identidad
por declaración. Los enlaces de herencia tienen detección de ciclos. La recuperación local
tolera nodos incompletos de ANTLR y sigue recorriendo las sentencias posteriores.

Consulta [las reglas y sus límites](SEMANTIC_RULES.md) para explicar los retornos por
caminos, los índices de arreglos y las pruebas de regresión.

### Tabla de símbolos

`backend/analyzer/symbol_table.py` mantiene un árbol de alcances. Cada `Scope` enlaza padre e hijos y guarda sus símbolos en un diccionario.

Operaciones principales:

```python
table.define_symbol(symbol)                         # insertar
table.lookup_symbol("name")                        # recuperar
table.update_symbol("name", is_initialized=True)  # actualizar
table.enter_scope("function", "sum")              # abrir alcance
table.exit_scope()                                  # volver al padre
```

Los alcances se serializan completos para mostrarlos en el IDE.

### Layout y generación intermedia

`layout.py` asigna una dirección única por símbolo, offsets en celdas de ocho bytes
y un registro por global, función o clase. Todos los bloques de una función usan
el mismo frame con direcciones distintas. Conserva los enlaces léxicos y calcula
los campos heredados y las etiquetas de métodos sobrescritos.

`tac.py` recorre el mismo árbol validado y reutiliza los alcances y símbolos
resueltos en el visitor semántico. No reconstruye un parser. Genera cuádruplas
`op, arg1, arg2, result`, etiquetas, llamadas y operaciones de objetos.
`TemporaryPool` separa temporales vivos y libres por función; libera un temporal
después de su último uso y mantiene reservados los valores que deben sobrevivir
a ramas, ciclos o argumentos anidados.

La puerta de generación comprueba **todas** las listas de errores. La recuperación
puede producir un árbol y símbolos parciales, pero nunca produce TAC desde un
programa inválido. Los detalles están en [TAC_DESIGN.md](TAC_DESIGN.md).

### Diagramas y archivos

`diagrams.py` construye grafos DOT y llama a Graphviz mediante argumentos separados,
sin shell. Produce SVG para previsualizar y PNG para descargar. El árbol conserva
las reglas de ANTLR; los símbolos muestran alcances y offsets; el TAC se divide
en bloques básicos con aristas de salto, continuación y excepción.

Cada solicitud recibe una carpeta única bajo `output/diagrams/`. La API sirve
solo esa carpeta con `StaticFiles`; no expone el resto del repositorio. También
guarda `program.tac` y el JSON del TAC válido. El render tiene un tiempo límite;
un fallo de Graphviz se informa como aviso sin perder los resultados del análisis.

### API

`backend/server.py` expone:

- `POST /compile`: analiza el texto del editor;
- `POST /compile/file`: recibe un archivo `.cps` UTF-8;
- `GET /health`: comprueba disponibilidad;
- `GET /info`: describe las capacidades.
- `GET /diagrams/<id>/<archivo>`: sirve las imágenes guardadas.

La respuesta incluye contadores, errores, tokens, árbol, símbolos, `intermediateCode`,
`diagrams` y `diagramWarnings`. El análisis y render se ejecutan en un threadpool
para evitar bloquear el bucle de la API.

### IDE

`frontend/src/App.tsx` usa React, TypeScript y Monaco. La interfaz ofrece:

- apertura y arrastre de archivos `.cps`;
- resaltado propio para Compiscript;
- marcadores y navegación a la línea del error;
- pestañas de diagnósticos, árbol, símbolos y tokens;
- pestaña TAC con imagen del flujo de control y texto intermedio;
- previsualización de imágenes con zoom, descarga y ruta guardada;
- ejemplos válidos y con varios errores;
- distribución adaptable para pantallas pequeñas.

Si el usuario cambia el código durante un análisis, una revisión del editor
impide mostrar la respuesta anterior como si perteneciera al texto nuevo.

## Pruebas

`pytest.ini` agrega `backend/` al path y limita el descubrimiento a `tests/`. La batería incluye tipos, tabla de símbolos, reglas semánticas, recuperación de errores y programas `.cps`.

Comandos de verificación:

```bash
python -m pytest -v
cd frontend && npm run build
```
