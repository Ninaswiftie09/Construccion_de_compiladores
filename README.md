# Compiscript - analizador e IDE

Proyecto de Construcción de Compiladores para analizar programas Compiscript. El sistema cubre únicamente las fases léxica, sintáctica y semántica; no ejecuta código ni genera código intermedio u objeto.

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

## Inicio rápido

Requisitos: Python 3.10 o superior, Node.js 18 o superior, Java 11 o superior y Git.

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

## Estructura

```text
backend/
  analyzer/       Orquestador, visitor semántico y tabla de símbolos
  grammar/        Gramática ANTLR
  models/         Tipos, símbolos y errores
  server.py       API FastAPI
frontend/
  src/            IDE React y estilos
tests/            Pruebas unitarias, integrales y casos Compiscript
docs/              Instalación y arquitectura
```

Los archivos generados por ANTLR, entornos virtuales, dependencias de Node y la carpeta local `instrucciones/` están excluidos de Git.

Consulta [la guía de instalación](docs/SETUP.md) y [la arquitectura](docs/ARCHITECTURE.md) para más detalle.
