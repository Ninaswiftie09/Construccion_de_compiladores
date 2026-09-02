# Installation & Setup Guide

## Prerequisites

- **Python 3.9+** - For backend
- **Node.js 16+** - For frontend
- **ANTLR 4.14+** - Parser generator
- **Git** - Version control

## Step 1: Clone the Repository

```bash
git clone <repository-url>
cd Construccion_de_compiladores
```

## Step 2: Backend Setup

### Install Python Dependencies

```bash
cd backend
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Generate ANTLR Parser

```bash
cd grammar

# Generate Python files from grammar
antlr4 -Dlanguage=Python3 -visitor -listener Compiscript.g4

cd ..
```

You should see these files generated:
- `CompiscriptLexer.py`
- `CompiscriptParser.py`
- `CompiscriptListener.py`
- `CompiscriptVisitor.py`

### Run Backend Server

```bash
python server.py
```

Output:
```
🚀 Starting Compiscript Compiler API...
📍 Server running at http://localhost:8000
📚 API documentation at http://localhost:8000/docs
```

## Step 3: Frontend Setup

In a new terminal:

```bash
cd frontend
npm install
npm start
```

The IDE will open at `http://localhost:3000`

## Step 4: Running Tests

### Backend Tests

```bash
cd backend
cd tests
python -m pytest test_*.py -v
```

### Test a Specific File

```bash
python -m pytest test_symbol_table.py -v
```

## Testing the Compiler

### Method 1: Web IDE

1. Open http://localhost:3000
2. Write Compiscript code in the editor
3. Click "Compile"
4. View results in the right panel

### Method 2: API Testing

Use `curl` or Postman:

```bash
curl -X POST http://localhost:8000/compile \
  -H "Content-Type: application/json" \
  -d '{
    "code": "let x: integer = 10; print(x);"
  }'
```

### Method 3: Upload File

1. Create a `.cps` file with Compiscript code
2. In IDE, click "Load File"
3. Select your `.cps` file
4. Click "Compile"

## Example Test Cases

### Valid Program

```compiscript
let x: integer = 10;
let y: integer = 20;
print(x + y);
```

### Function Program

```compiscript
function add(a: integer, b: integer): integer {
  return a + b;
}

let result: integer = add(5, 3);
print(result);
```

### Type Error Example

```compiscript
let x: integer = "hello";  // Error: Cannot assign string to integer
```

### Undeclared Variable Example

```compiscript
print(undefined_var);  // Error: Undeclared variable
```

## Troubleshooting

### ANTLR Files Not Found

**Error**: "ANTLR generated files not found"

**Solution**:
```bash
cd backend/grammar
antlr4 -Dlanguage=Python3 -visitor -listener Compiscript.g4
cd ..
```

### Port Already in Use

**Error**: "Address already in use"

**Solution**: Change port in `server.py`:
```python
uvicorn.run(..., port=8001)  # Use different port
```

### Module Not Found

**Error**: "ModuleNotFoundError: No module named 'antlr4'"

**Solution**:
```bash
cd backend
pip install -r requirements.txt
```

### Frontend Can't Connect to Backend

**Error**: "Failed to connect to compiler server"

**Solution**:
1. Ensure backend is running: `python backend/server.py`
2. Check backend is on http://localhost:8000
3. Check firewall settings

### Monaco Editor Not Loading

**Error**: Blank editor in IDE

**Solution**:
```bash
cd frontend
npm install @monaco-editor/react
npm start
```

## Development Tips

### Running Backend in Debug Mode

```bash
cd backend
python -u server.py
```

### Hot Reload Frontend

Frontend automatically reloads on file changes.

### Checking API Documentation

Visit: http://localhost:8000/docs

Interactive Swagger UI for testing endpoints.

### Monitoring Compilation

Add debug output in `backend/analyzer/compiler.py`:

```python
def compile(self, source_code: str):
    print(f"Compiling {len(source_code)} characters...")
    # ... rest of method
```

## Project Structure

After setup, your structure should look like:

```
Construccion_de_compiladores/
├── backend/
│   ├── grammar/
│   │   ├── Compiscript.g4
│   │   ├── CompiscriptLexer.py      # Generated
│   │   ├── CompiscriptParser.py     # Generated
│   │   └── ...
│   ├── analyzer/
│   ├── models/
│   ├── venv/                         # Virtual environment
│   ├── server.py
│   └── requirements.txt
├── frontend/
│   ├── node_modules/                 # NPM packages
│   ├── src/
│   ├── public/
│   └── package.json
├── tests/
│   ├── test_cases/
│   ├── test_*.py
│   └── ...
├── docs/
│   ├── ARCHITECTURE.md
│   ├── SETUP.md (this file)
│   └── ...
└── README.md
```

## Next Steps

1. Review [ARCHITECTURE.md](./ARCHITECTURE.md) for design details
2. Check test files to understand test patterns
3. Read grammar file: `backend/grammar/Compiscript.g4`
4. Explore example programs in `tests/test_cases/`

## Performance

- Compilation of 1KB file: < 100ms
- IDE response time: < 200ms
- Memory usage: ~50MB (Python backend)

## Support

For issues or questions:
1. Check troubleshooting section
2. Review error messages carefully
3. Check backend logs in terminal
4. Consult architecture documentation
