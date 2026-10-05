# Compiscript - analizador e IDE

Proyecto de Construcción de Compiladores para analizar programas Compiscript y generar código intermedio de tres direcciones (TAC). Cubre las fases léxica, sintáctica, semántica y de representación intermedia. No ejecuta los programas fuente ni genera código objeto.

## Integrantes

- Ingrid Nina Alessandra Nájera Marakovits, 231088
- Eliazar José Pablo Canastuj Matías, 23384
- Diego Alejandro Ramírez Velásquez, 23601

## Funcionalidad

- Lexer y parser generados con ANTLR 4.13.2.
- Recuperación de errores en las tres fases para reportar varios problemas por análisis.
- Verificación de tipos, asignaciones, condiciones, arreglos y comparaciones.
- Funciones recursivas y anidadas, parámetros, argumentos y tipos de retorno.
- Clases, herencia, constructores, `this` y acceso a miembros.
- Validación de `break`, `continue`, `return` y código inalcanzable.
- Tabla de símbolos jerárquica con inserción, consulta, actualización y alcances.
- IDE web con editor, selección de archivos `.cps`, diagnósticos, árbol sintáctico, símbolos y tokens.
- TAC para expresiones, arreglos, control de flujo, funciones, recursión, clases, herencia y `try/catch`.
- Cortocircuito lógico, evaluación de argumentos en orden y reciclaje de temporales por función.
- Direcciones simbólicas, offsets, registros de activación, enlaces estáticos y layouts de objetos.
- Diagramas de árbol, símbolos y flujo TAC con previsualización, zoom y descarga PNG.
- Imágenes SVG/PNG y archivos TAC guardados en `output/diagrams/<id>/`.
- Bloqueo completo del TAC si existe cualquier error léxico, sintáctico o semántico.

## Inicio rápido

Requisitos: Python 3.10 o superior, Node.js 18 o superior, Java 11 o superior, Git y Graphviz (`dot` en el PATH).

En Windows:

```bat
setup.bat
```

En Linux o macOS:

```bash
chmod +x setup.sh generate_parser.sh
./setup.sh
```

Después, inicia cada servicio en una terminal distinta:

```bash
python quickstart.py backend
python quickstart.py frontend
```

Abre `http://localhost:3000`. La API y su documentación estarán en `http://localhost:8000` y `http://localhost:8000/docs`.

## Pruebas

Desde la raíz:

```bash
python quickstart.py test
```

También puedes ejecutar directamente:

```bash
python -m pytest -v
cd frontend
npm run build
```

Los casos `.cps` para demostración se encuentran en `tests/test_cases/`.
Los casos `valid_tac_*.cps` cubren la segunda parte; `error_tac_blocked.cps` demuestra varios errores sin TAC.

Pruebas de interfaz:

```bash
cd frontend
npm test -- --watchAll=false --runInBand
```

## Estructura

```text
backend/
  analyzer/       Análisis, tabla de símbolos, layout, TAC y diagramas
  grammar/        Gramática ANTLR
  models/         Tipos, símbolos y errores
  server.py       API FastAPI
frontend/
  src/            IDE React y estilos
tests/            Pruebas unitarias, integrales y casos Compiscript
docs/              Instalación y arquitectura
output/diagrams/  Imágenes y TAC de cada análisis (archivos locales)
```

Los archivos generados por ANTLR, entornos virtuales, dependencias de Node y la carpeta local `instrucciones/` están excluidos de Git.

Consulta [la guía de instalación](docs/SETUP.md) y [la arquitectura](docs/ARCHITECTURE.md) para más detalle.

La [guía de reglas semánticas](docs/SEMANTIC_RULES.md) explica las decisiones del
analizador, los límites de la comprobación estática y los casos para la presentación.

El [diseño del TAC](docs/TAC_DESIGN.md) define cada instrucción, el manejo de memoria,
los registros de activación, los supuestos y ejemplos de traducción. La
[matriz de cumplimiento](docs/PROJECT_02_CHECKLIST.md) relaciona cada criterio con
su implementación y pruebas.
