import React, { useState, useCallback } from 'react';
import axios from 'axios';
import Editor from '@monaco-editor/react';
import './App.css';

interface CompilationError {
  type: string;
  message: string;
  line: number;
  column: number;
  context?: string;
}

interface CompilationResult {
  success: boolean;
  totalErrors: number;
  lexicalErrors: number;
  syntacticErrors: number;
  semanticErrors: number;
  errors: CompilationError[];
  tokenCount: number;
}

function App() {
  const [code, setCode] = useState('// Welcome to Compiscript IDE\n\nlet x: integer = 10;\nlet y: integer = 20;\nprint(x + y);');
  const [result, setResult] = useState<CompilationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleCompile = useCallback(async () => {
    setLoading(true);
    try {
      const response = await axios.post<CompilationResult>('/compile', {
        code: code
      });
      setResult(response.data);
    } catch (error) {
      setResult({
        success: false,
        totalErrors: 1,
        lexicalErrors: 0,
        syntacticErrors: 0,
        semanticErrors: 0,
        errors: [{
          type: 'error',
          message: 'Failed to connect to compiler server',
          line: 0,
          column: 0
        }],
        tokenCount: 0
      });
    } finally {
      setLoading(false);
    }
  }, [code]);

  const handleFileUpload = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.cps')) {
      alert('Please select a .cps file');
      return;
    }

    setSelectedFile(file);
    const text = await file.text();
    setCode(text);
  }, []);

  const handleDownloadExample = () => {
    const exampleCode = `// Ejemplo: Factorial
function factorial(n: integer): integer {
  if (n <= 1) {
    return 1;
  }
  return n * factorial(n - 1);
}

let result: integer = factorial(5);
print(result);`;
    setCode(exampleCode);
  };

  const getErrorColor = (errorType: string) => {
    switch (errorType) {
      case 'lexical': return '#FF6B6B';
      case 'syntactic': return '#FFA500';
      case 'semantic': return '#FFD700';
      default: return '#999';
    }
  };

  return (
    <div className="App">
      <header className="header">
        <div className="header-content">
          <h1>🧪 Compiscript Compiler IDE</h1>
          <p>Lexical, Syntactic & Semantic Analysis</p>
        </div>
      </header>

      <div className="container">
        <div className="editor-section">
          <div className="editor-toolbar">
            <div className="toolbar-group">
              <button 
                className="btn btn-primary" 
                onClick={handleCompile}
                disabled={loading}
              >
                {loading ? '⏳ Compiling...' : '▶ Compile'}
              </button>
              <label className="btn btn-secondary">
                📁 Load File
                <input
                  type="file"
                  accept=".cps"
                  onChange={handleFileUpload}
                  style={{ display: 'none' }}
                />
              </label>
              <button className="btn btn-secondary" onClick={handleDownloadExample}>
                📝 Example
              </button>
            </div>
            {selectedFile && <span className="file-name">📄 {selectedFile.name}</span>}
          </div>

          <div className="editor-container">
            <Editor
              height="100%"
              defaultLanguage="javascript"
              value={code}
              onChange={(value) => setCode(value || '')}
              theme="vs-dark"
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                fontFamily: "'Fira Code', 'Consolas', monospace",
                lineNumbers: 'on',
              }}
            />
          </div>
        </div>

        <div className="results-section">
          <div className="results-header">
            <h2>📊 Analysis Results</h2>
            {result && (
              <div className={`status ${result.success ? 'success' : 'error'}`}>
                {result.success ? '✅ Success' : '❌ Errors Found'}
              </div>
            )}
          </div>

          {result && (
            <div className="results-container">
              <div className="results-summary">
                <div className="summary-item">
                  <span className="label">Total Errors:</span>
                  <span className="value">{result.totalErrors}</span>
                </div>
                <div className="summary-item">
                  <span className="label">Lexical:</span>
                  <span className="value lexical">{result.lexicalErrors}</span>
                </div>
                <div className="summary-item">
                  <span className="label">Syntactic:</span>
                  <span className="value syntactic">{result.syntacticErrors}</span>
                </div>
                <div className="summary-item">
                  <span className="label">Semantic:</span>
                  <span className="value semantic">{result.semanticErrors}</span>
                </div>
                <div className="summary-item">
                  <span className="label">Tokens:</span>
                  <span className="value">{result.tokenCount}</span>
                </div>
              </div>

              {result.errors.length > 0 && (
                <div className="errors-list">
                  <h3>Errors ({result.errors.length})</h3>
                  {result.errors.map((error, index) => (
                    <div
                      key={index}
                      className="error-item"
                      style={{ borderLeftColor: getErrorColor(error.type) }}
                    >
                      <div className="error-type">{error.type.toUpperCase()}</div>
                      <div className="error-location">Line {error.line}, Column {error.column}</div>
                      <div className="error-message">{error.message}</div>
                      {error.context && <div className="error-context">Context: {error.context}</div>}
                    </div>
                  ))}
                </div>
              )}

              {result.success && (
                <div className="success-message">
                  🎉 Code compiled successfully without errors!
                </div>
              )}
            </div>
          )}

          {!result && (
            <div className="empty-state">
              <p>👈 Click "Compile" to analyze your code</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
