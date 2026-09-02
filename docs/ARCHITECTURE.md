# Architecture Documentation

## Project Overview

The Compiscript Compiler is a three-phase compiler with an integrated IDE:
1. **Lexical Analysis** - Tokenization
2. **Syntactic Analysis** - AST generation
3. **Semantic Analysis** - Type checking and scope validation

## Architecture Components

### Backend (Python)

```
backend/
├── grammar/
│   ├── Compiscript.g4          # ANTLR grammar
│   ├── CompiscriptLexer.py      # Generated lexer
│   └── CompiscriptParser.py     # Generated parser
├── analyzer/
│   ├── compiler.py              # Main compiler orchestrator
│   ├── semantic.py              # Semantic analyzer & type checker
│   └── symbol_table.py          # Symbol table with scope management
├── models/
│   ├── error.py                 # Error representation
│   ├── types.py                 # Type system & symbol definitions
│   └── __init__.py
├── server.py                    # FastAPI server
└── requirements.txt             # Python dependencies
```

### Frontend (React + TypeScript)

```
frontend/
├── public/
│   └── index.html               # HTML entry point
├── src/
│   ├── App.tsx                  # Main component
│   ├── App.css                  # Styling
│   ├── index.tsx                # React entry point
│   └── index.css                # Global styles
├── package.json                 # Dependencies
└── tsconfig.json                # TypeScript config
```

## Analysis Pipeline

### Phase 1: Lexical Analysis
- **Input**: Source code string
- **Process**: 
  - ANTLR Lexer tokenizes input
  - Recovers from unknown tokens
  - Continues to find all lexical errors
- **Output**: Token stream, lexical errors
- **Error Recovery**: Skips unrecognized characters and continues

### Phase 2: Syntactic Analysis
- **Input**: Token stream from lexer
- **Process**:
  - ANTLR Parser builds AST
  - Implements panic mode error recovery
  - Reports all syntax errors found
- **Output**: AST, syntactic errors
- **Error Recovery**: Synchronizes to next statement on errors

### Phase 3: Semantic Analysis
- **Input**: AST from parser
- **Process**:
  - Tree walk visitor traverses AST
  - Symbol table tracks variables and functions
  - Type checker validates operations
  - Scope validator ensures proper name resolution
- **Output**: Semantic errors, annotated AST
- **Error Recovery**: Continues analyzing after type errors

## Core Classes

### `Compiler`
Main orchestrator that coordinates all phases. Entry point for compilation.

```python
result = compiler.compile(source_code)
# Returns CompilationResult with all errors
```

### `SymbolTable`
Hierarchical symbol table with scope management.

Features:
- Global, function, class, and block scopes
- Parent scope lookup (variable resolution)
- Loop and function context tracking
- Scope hierarchy queries

```python
table.enter_scope("function")
table.define_symbol(symbol)
symbol = table.lookup_symbol("name")  # Searches current + parent scopes
table.exit_scope()
```

### `SemanticAnalyzer`
Validates types, scopes, and semantic rules.

Key operations:
- Type checking: arithmetic, logical, comparison operations
- Assignment validation
- Function call validation (arity and types)
- Control flow validation (break/continue/return placement)
- Variable declaration and resolution

### `CompilationResult`
Collects all errors and metadata from compilation.

```python
result.lexical_errors     # List of lexical errors
result.syntactic_errors   # List of syntactic errors
result.semantic_errors    # List of semantic errors
result.tokens             # List of tokens generated
result.ast                # Abstract syntax tree
```

## Data Types

Supported types:
- `integer` - 32-bit integers
- `float` - Floating point numbers
- `string` - Text strings
- `boolean` - true/false values
- `null` - Null/none value
- `array` - Collections (type generic)
- `object` - Class instances

Type compatibility rules:
- Same types are directly assignable
- `NULL` is compatible with all types
- `integer` can be assigned to `float`
- Numeric types (`integer`, `float`) can be used in arithmetic operations
- `boolean` types required for logical operations

## Error Recovery Strategy

### Lexical Errors
- Unrecognized characters are skipped
- Lexer continues tokenizing remainder of input
- No fatal errors

### Syntactic Errors
- Panic mode recovery: skip tokens until synchronization point
- Synchronization points: statement boundaries, block delimiters
- Multiple errors reported per execution

### Semantic Errors
- Analysis continues after type errors
- Symbol table maintains state across errors
- All semantic violations reported in one pass

## API Endpoints

### `POST /compile`
Compile source code provided as string.

Request:
```json
{
  "code": "let x: integer = 10; print(x);"
}
```

Response:
```json
{
  "success": true,
  "totalErrors": 0,
  "lexicalErrors": 0,
  "syntacticErrors": 0,
  "semanticErrors": 0,
  "errors": [],
  "tokenCount": 8
}
```

### `POST /compile/file`
Compile file uploaded as multipart form-data.

### `GET /health`
Health check endpoint.

## Frontend Features

### Editor
- Monaco Editor integration with syntax highlighting
- Real-time error display
- Line numbers and code folding

### Results Panel
- Error summary (lexical, syntactic, semantic)
- Detailed error list with line/column info
- Token count statistics
- File upload and example loading

### UI/UX
- Dark theme optimized for coding
- Responsive design (mobile-friendly)
- Smooth animations and transitions
- Intuitive error visualization with color coding

## Semantic Rules Implemented

### Type System
- ✓ Arithmetic operations require numeric types
- ✓ Logical operations require boolean types
- ✓ Comparison operations validate type compatibility
- ✓ Assignment type checking

### Scope Management
- ✓ Variable declaration and resolution
- ✓ Scope hierarchy (global, function, block)
- ✓ No redeclaration in same scope
- ✓ Closure variable capture

### Control Flow
- ✓ Break/continue must be in loops
- ✓ Return must be in functions
- ✓ Conditional expressions must be boolean

### Functions
- ✓ Function declaration and lookup
- ✓ Parameter arity checking
- ✓ Parameter type validation
- ✓ Return type consistency

## Testing Strategy

### Unit Tests
- `test_types.py` - Type system validation
- `test_symbol_table.py` - Symbol table operations

### Integration Tests
- Test files in `tests/test_cases/` - Full compilation scenarios

Test categories:
- Valid programs
- Lexical errors
- Syntactic errors
- Semantic errors (type mismatches, undeclared variables)

## Performance Considerations

- Single-pass lexical analysis: O(n) where n = source length
- Single-pass syntactic analysis: O(n) with memoization
- Single-pass semantic analysis: O(n)
- Symbol table lookup: O(1) average (hash map), O(d) with scope depth
- Overall compilation: O(n)

## Future Enhancements

- Code generation (intermediate representation)
- Optimization passes
- Runtime execution
- Debugging information (debug symbols)
- Extended standard library
- Module system
- Generics support
