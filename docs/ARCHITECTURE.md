# Arquitectura

## Alcance

El proyecto implementa análisis estático de Compiscript. La salida contiene diagnósticos, tokens, árbol sintáctico y tabla de símbolos. No existe fase de ejecución ni generación de código.

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

### API

`backend/server.py` expone:

- `POST /compile`: analiza el texto del editor;
- `POST /compile/file`: recibe un archivo `.cps` UTF-8;
- `GET /health`: comprueba disponibilidad;
- `GET /info`: describe las capacidades.

La respuesta de compilación incluye contadores por fase, lista de errores, tokens, árbol y tabla de símbolos.

### IDE

`frontend/src/App.tsx` usa React, TypeScript y Monaco. La interfaz ofrece:

- apertura y arrastre de archivos `.cps`;
- resaltado propio para Compiscript;
- marcadores y navegación a la línea del error;
- pestañas de diagnósticos, árbol, símbolos y tokens;
- ejemplos válidos y con varios errores;
- distribución adaptable para pantallas pequeñas.

## Pruebas

`pytest.ini` agrega `backend/` al path y limita el descubrimiento a `tests/`. La batería incluye tipos, tabla de símbolos, reglas semánticas, recuperación de errores y programas `.cps`.

Comandos de verificación:

```bash
python -m pytest -v
cd frontend && npm run build
```
