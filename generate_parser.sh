#!/bin/bash

# Generate ANTLR parser files for Compiscript
# Usage: ./generate_parser.sh

set -e

echo "🔨 Generating ANTLR Parser for Compiscript"
echo "==========================================="

cd "$(dirname "$0")/backend/grammar"
export ANTLR4_TOOLS_ANTLR_VERSION=4.13.2

if ! command -v antlr4 &> /dev/null; then
  echo "❌ Error: antlr4 not found"
  echo ""
  echo "Please install ANTLR first:"
  echo "  macOS:  brew install antlr"
  echo "  Linux:  sudo apt-get install antlr4"
  echo "  Or run: pip install antlr4-tools==0.2.2"
  exit 1
fi

echo "📝 Grammar file: Compiscript.g4"
echo "🎯 Target language: Python 3"
echo ""

# Generate parser
echo "Generating lexer, parser, visitor, and listener..."
antlr4 -Dlanguage=Python3 -visitor -listener Compiscript.g4

echo ""
echo "✅ Parser generation complete!"
echo ""
echo "Generated files:"
ls -la *.py | grep -E "(Lexer|Parser|Visitor|Listener)" || echo "No files generated"

cd - > /dev/null
