"""
FastAPI server for the Compiscript Compiler
Provides REST API endpoints for compilation and analysis
"""
import os
import sys
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Optional

# Add backend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from analyzer.compiler import Compiler, CompilationResult


# ===== Pydantic Models =====

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


# ===== FastAPI App Setup =====

app = FastAPI(
    title="Compiscript Compiler API",
    description="Lexical, syntactic, and semantic analysis for Compiscript",
    version="1.0.0"
)

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== Routes =====

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "Compiscript Compiler API",
        "version": "1.0.0"
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
        compiler = Compiler()
        result = compiler.compile(request.code)
        
        return CompileResponse(**result.to_dict())
    
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
        # Check file extension
        if not file.filename.endswith('.cps'):
            raise HTTPException(
                status_code=400,
                detail="File must be a .cps file"
            )
        
        # Read file content
        content = await file.read()
        try:
            source_code = content.decode('utf-8')
        except UnicodeDecodeError as error:
            raise HTTPException(status_code=400, detail="File must use UTF-8 encoding") from error
        
        # Compile
        compiler = Compiler()
        result = compiler.compile(source_code)
        
        return CompileResponse(**result.to_dict())
    
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
        "version": "1.0.0",
        "features": [
            "Lexical Analysis",
            "Syntactic Analysis",
            "Semantic Analysis",
            "Symbol Table Management",
            "Error Recovery"
        ],
        "supportedTypes": [
            "integer",
            "float",
            "string",
            "boolean",
            "null"
        ]
    }


# ===== Development Server =====

if __name__ == "__main__":
    import uvicorn
    
    # Check if ANTLR files are generated
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
