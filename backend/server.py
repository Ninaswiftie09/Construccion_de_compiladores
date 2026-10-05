"""
FastAPI server for the Compiscript Compiler
Provides REST API endpoints for compilation and analysis
"""
import os
import sys
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from pydantic import Field
from pydantic import BaseModel
from typing import Any, Optional

# Permite importar el analizador al iniciar este archivo directamente.
sys.path.insert(0, str(Path(__file__).parent))

from analyzer.compiler import Compiler, CompilationResult
from analyzer.diagrams import OUTPUT_DIR, save_diagrams


# Pydantic valida el formato de las solicitudes y respuestas.

class CompileRequest(BaseModel):
    """Request model for code compilation"""
    code: str


class CompileResponse(BaseModel):
    """Response model for compilation results"""
    success: bool
    totalErrors: int
    lexicalErrors: int
    syntacticErrors: int
    semanticErrors: int
    errors: list
    tokenCount: int
    tokens: list[dict[str, Any]]
    ast: Optional[dict[str, Any]] = None
    symbolTable: Optional[dict[str, Any]] = None
    intermediateCode: Optional[dict[str, Any]] = None
    diagrams: dict[str, Any] = Field(default_factory=dict)
    diagramWarnings: list[str] = Field(default_factory=list)


# Crea la API que conecta el IDE con el analizador.

app = FastAPI(
    title="Compiscript Compiler API",
    description="Compiscript analysis, TAC generation and image diagrams",
    version="2.0.0"
)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/diagrams", StaticFiles(directory=OUTPUT_DIR), name="diagrams")


def build_response(code):
    result = Compiler().compile(code)
    diagrams, warnings = save_diagrams(result)
    return CompileResponse(**result.to_dict(), diagrams=diagrams, diagramWarnings=warnings)

# CORS permite conectar una interfaz servida desde otro puerto.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configuracion de desarrollo local
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Cada ruta recibe datos o informa el estado del servicio.

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "Compiscript Compiler API",
        "version": "2.0.0"
    }


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy"}


@app.post("/compile")
async def compile_code(request: CompileRequest) -> CompileResponse:
    """
    Compile Compiscript source code.
    
    Performs lexical, syntactic, and semantic analysis.
    Returns all errors found in a single execution.
    """
    try:
        # Cada solicitud usa una tabla y una lista de errores independientes.
        return await run_in_threadpool(build_response, request.code)
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Compilation error: {str(e)}"
        )


@app.post("/compile/file")
async def compile_file(file: UploadFile = File(...)) -> CompileResponse:
    """
    Compile a Compiscript file.
    
    Accepts .cps file upload and performs full analysis.
    """
    try:
        # Rechaza formatos que no correspondan a archivos Compiscript.
        if not (file.filename or "").lower().endswith('.cps'):
            raise HTTPException(
                status_code=400,
                detail="File must be a .cps file"
            )
        
        # Decodifica UTF-8 antes de enviar el texto al analizador.
        content = await file.read()
        try:
            source_code = content.decode('utf-8')
        except UnicodeDecodeError as error:
            raise HTTPException(status_code=400, detail="File must use UTF-8 encoding") from error
        
        # Analiza el archivo sin ejecutar sus instrucciones.
        # Cada solicitud usa una tabla y una lista de errores independientes.
        return await run_in_threadpool(build_response, source_code)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"File compilation error: {str(e)}"
        )


@app.get("/info")
async def compiler_info():
    """Get information about the compiler"""
    return {
        "name": "Compiscript Compiler",
        "version": "2.0.0",
        "features": [
            "Lexical Analysis",
            "Syntactic Analysis",
            "Semantic Analysis",
            "Symbol Table Management",
            "Error Recovery",
            "Three Address Code",
            "Temporary Recycling",
            "Activation Records",
            "Saved Image Diagrams"
        ],
        "supportedTypes": [
            "integer",
            "float",
            "string",
            "boolean",
            "null"
        ]
    }


# Punto de entrada para iniciar el servidor durante el desarrollo.

if __name__ == "__main__":
    import uvicorn
    
    # Avisa cuando faltan las clases generadas por ANTLR.
    grammar_dir = Path(__file__).parent / "grammar"
    lexer_file = grammar_dir / "CompiscriptLexer.py"
    parser_file = grammar_dir / "CompiscriptParser.py"
    
    if not lexer_file.exists() or not parser_file.exists():
        print("Warning: ANTLR generated files not found!")
        print("Please run: cd backend/grammar && antlr4 -Dlanguage=Python3 -visitor -listener Compiscript.g4")
        print()
    
    print("Starting Compiscript Compiler API...")
    print("Server running at http://localhost:8000")
    print("API documentation at http://localhost:8000/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
