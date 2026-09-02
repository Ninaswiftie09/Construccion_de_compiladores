# Compiscript Compiler & IDE

## Integrantes:
- Ingrid Nina Alessandra Nájera Marakovits, 231088
- Eliazar José Pablo Canastuj Matías, 23384
- Diego Alejandro Ramírez Velásquez, 23601

---

## 📋 Descripción del Proyecto

Implementación completa de un compilador para el lenguaje **Compiscript** con análisis léxico, sintáctico y semántico, más una interfaz IDE moderna e intuitiva.

## ✨ Características

✅ **Análisis Léxico** - Tokenización con recuperación de errores  
✅ **Análisis Sintáctico** - Generación de AST con recuperación de errores  
✅ **Análisis Semántico** - Verificación de tipos, manejo de scopes y validación  
✅ **Tabla de Símbolos** - Gestión completa de entornos y ámbitos  
✅ **IDE Integrado** - Interfaz moderna e intuitiva  
✅ **Reportes de Errores** - Múltiples errores por ejecución con mensajes detallados  
✅ **Suite de Pruebas** - Tests completos para todas las fases  

## 📂 Estructura del Proyecto

```
.
├── backend/                    # Backend Python
│   ├── grammar/               # Gramática ANTLR y archivos generados
│   ├── analyzer/              # Implementación de análisis
│   │   ├── lexer.py           # Lógica del analizador léxico
│   │   ├── parser.py          # Wrapper del parser
│   │   ├── semantic.py        # Analizador semántico
│   │   └── symbol_table.py    # Tabla de símbolos y manejo de scopes
│   ├── models/                # Estructuras de datos
│   ├── server.py              # Servidor FastAPI
│   └── requirements.txt        # Dependencias Python
├── frontend/                   # Frontend React TypeScript
│   ├── src/
│   │   ├── components/        # Componentes UI
│   │   ├── pages/            # Páginas
│   │   ├── styles/           # Estilos
│   │   └── App.tsx           # App principal
│   └── package.json
├── tests/                      # Suite de pruebas
│   ├── test_cases/            # Casos de prueba .cps
│   └── test_*.py              # Archivos de test
└── docs/                       # Documentación
```

## 🚀 Quick Start

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Generar parser desde gramática ANTLR
cd grammar
antlr4 -Dlanguage=Python3 -visitor -listener Compiscript.g4
cd ..

python server.py
```

### Frontend

```bash
cd frontend
npm install
npm start
```

El IDE estará disponible en `http://localhost:3000`

## 🧪 Testing

```bash
cd tests
python -m pytest test_*.py -v
```

## 📝 Requisitos Cumplidos

✓ Análisis léxico con recuperación de errores  
✓ Análisis sintáctico con recuperación de errores  
✓ Análisis semántico con recuperación de errores  
✓ Sistema de tipos (aritmética, lógica, comparaciones)  
✓ Manejo de ámbitos y resolución de nombres  
✓ Validación de funciones y parámetros  
✓ Validación de control de flujo  
✓ Validación de clases y acceso a miembros  
✓ Tabla de símbolos completa  
✓ IDE con interfaz gráfica  
✓ Reportes de múltiples errores