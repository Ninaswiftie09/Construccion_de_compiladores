# Instalación y ejecución

## Requisitos

- Python 3.10+
- Node.js 18+
- Java 11+ disponible como `java`
- Git
- Graphviz con `dot` en el PATH

ANTLR se instala mediante `antlr4-tools` y descarga el JAR 4.13.2 la primera vez que se genera el parser.

Instala Graphviz antes de analizar. Windows: `winget install Graphviz.Graphviz`;
Ubuntu: `sudo apt-get install graphviz`; macOS: `brew install graphviz`.
Abre otra terminal y comprueba `dot -V`. Graphviz dibuja los resultados; no ejecuta Compiscript.

## Instalación automática

Windows:

```bat
setup.bat
```

Linux o macOS:

```bash
chmod +x setup.sh generate_parser.sh dev.sh
./setup.sh
```

Los scripts crean `backend/venv`, instalan las dependencias, generan lexer/parser/visitor y ejecutan `npm install`.

## Instalación manual

### Backend

```bash
cd backend
python -m venv venv
```

Activa el entorno:

```bash
# Windows PowerShell
venv\Scripts\Activate.ps1

# Linux o macOS
source venv/bin/activate
```

Instala y genera ANTLR:

```bash
pip install -r requirements.txt
cd grammar

# PowerShell
$env:ANTLR4_TOOLS_ANTLR_VERSION="4.13.2"

# Linux o macOS
export ANTLR4_TOOLS_ANTLR_VERSION=4.13.2

antlr4 -Dlanguage=Python3 -visitor -listener Compiscript.g4
```

### Frontend

```bash
cd frontend
npm install
```

## Ejecución

Terminal 1:

```bash
python quickstart.py backend
```

Terminal 2:

```bash
python quickstart.py frontend
```

Direcciones:

- IDE: `http://localhost:3000`
- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

En el IDE puedes escribir código, abrir o arrastrar un archivo `.cps` y analizar con el botón principal o `Ctrl + Enter`.

Cuando el programa es válido aparece la pestaña **TAC**, con el diagrama de flujo,
las estadísticas de temporales y el texto intermedio. **Árbol** y **Símbolos**
muestran imágenes. Usa `+`, `−`, **Tamaño real**, **Ajustar** o **Abrir imagen completa** para inspeccionarlas.
El enlace **PNG** descarga una imagen ya guardada por el backend.

Cada análisis crea `output/diagrams/<id>/` en la raíz del proyecto. Ahí se guardan
`ast.svg/png/dot`, `symbols.svg/png/dot` y, solo si no hubo errores,
`tac.svg/png/dot`, `program.tac` y `program.json`. No se incluyen en Git.
Los programas con errores conservan diagnósticos y diagramas de análisis, pero no TAC.
Las carpetas anteriores se conservan para comparar análisis y pueden eliminarse
manualmente cuando ya no hagan falta; la UI siempre usa el resultado actual.

## Pruebas y build

```bash
python -m pytest -v
cd frontend
npm run build
npm test -- --watchAll=false --runInBand
```

## Regenerar el parser

Después de modificar `backend/grammar/Compiscript.g4`:

```bash
# Windows
generate_parser.bat

# Linux o macOS
./generate_parser.sh
```

Los archivos generados no se versionan; se reconstruyen desde la gramática.

## Problemas comunes

### No se encuentra `antlr4`

Activa `backend/venv` y vuelve a ejecutar `pip install -r backend/requirements.txt`.

### ANTLR no puede iniciar

Verifica `java -version`. El generador necesita una instalación funcional de Java.

### El frontend no conecta

Confirma que `http://localhost:8000/health` responda `{"status":"healthy"}` y que el frontend use el puerto 3000.

### PowerShell bloquea `npm.ps1`

Usa `npm.cmd install` y `npm.cmd start` en lugar de `npm`.

### Faltan diagramas

Comprueba `dot -V` en la misma terminal que inicia el backend. Si acabas de instalar
Graphviz, reinicia esa terminal y el servidor. Los avisos se muestran en el IDE;
el análisis y el texto TAC siguen disponibles si falla el render de una imagen.
