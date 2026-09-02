import React, { useCallback, useEffect, useRef, useState } from 'react';
import axios from 'axios';
import Editor from '@monaco-editor/react';
import './App.css';

interface CompilationError {
  type: 'lexical' | 'syntactic' | 'semantic' | 'connection';
  message: string;
  line: number;
  column: number;
  context?: string;
}

interface AstNode {
  name: string;
  text: string;
  line: number;
  children: AstNode[];
}

interface TokenInfo {
  type: string;
  value: string;
  line: number;
  column: number;
}

interface SymbolInfo {
  name: string;
  type: string;
  dataType: string;
  line: number;
  isConst: boolean;
  isInitialized: boolean;
  parameters: { name: string; type: string }[];
  returnType: string;
}

interface SymbolScope {
  type: string;
  name: string;
  symbols: SymbolInfo[];
  children: SymbolScope[];
}

interface CompilationResult {
  success: boolean;
  totalErrors: number;
  lexicalErrors: number;
  syntacticErrors: number;
  semanticErrors: number;
  errors: CompilationError[];
  tokenCount: number;
  tokens: TokenInfo[];
  ast: AstNode | null;
  symbolTable: SymbolScope | null;
}

type PanelTab = 'errors' | 'ast' | 'symbols' | 'tokens';

const initialCode = `// Analiza este programa con Ctrl + Enter
function fibonacci(n: integer): integer {
  if (n <= 1) {
    return n;
  }
  return fibonacci(n - 1) + fibonacci(n - 2);
}

let resultado: integer = fibonacci(8);
print(resultado);`;

const examples = {
  factorial: `// Recursion y validacion de funciones
function factorial(n: integer): integer {
  if (n <= 1) { return 1; }
  return n * factorial(n - 1);
}

let resultado: integer = factorial(5);
print(resultado);`,
  errors: `// El analizador reporta varios errores a la vez
let cantidad: integer = "diez";
print(noDeclarada);
break;
let activo: boolean = 1 && false;`,
};

function AstTree({ node, depth = 0 }: { node: AstNode; depth?: number }) {
  const isToken = node.name === 'token';
  if (isToken) {
    return <div className="tree-token"><span>{node.text || 'EOF'}</span><small>L{node.line}</small></div>;
  }
  return (
    <details className="tree-branch" open={depth < 2}>
      <summary><span>{node.name}</span><small>{node.children.length} nodos</small></summary>
      <div className="tree-children">
        {node.children.map((child, index) => <AstTree key={`${child.name}-${index}`} node={child} depth={depth + 1} />)}
      </div>
    </details>
  );
}

function ScopeTree({ scope, depth = 0 }: { scope: SymbolScope; depth?: number }) {
  return (
    <details className="scope-card" open={depth < 2}>
      <summary>
        <span className="scope-dot" />
        <strong>{scope.name || scope.type}</strong>
        <small>{scope.type} · {scope.symbols.length} símbolos</small>
      </summary>
      <div className="scope-content">
        {scope.symbols.length === 0 && <p className="muted-copy">Sin símbolos en este alcance.</p>}
        {scope.symbols.map((symbol) => (
          <div className="symbol-row" key={`${symbol.name}-${symbol.line}`}>
            <div><strong>{symbol.name}</strong><span>{symbol.type}</span></div>
            <code>{symbol.dataType}</code>
          </div>
        ))}
        {scope.children.map((child, index) => <ScopeTree key={`${child.name}-${index}`} scope={child} depth={depth + 1} />)}
      </div>
    </details>
  );
}

function App() {
  const [code, setCode] = useState(initialCode);
  const [result, setResult] = useState<CompilationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [fileName, setFileName] = useState('program.cps');
  const [activeTab, setActiveTab] = useState<PanelTab>('errors');
  const [isDragging, setIsDragging] = useState(false);
  const editorRef = useRef<any>(null);
  const monacoRef = useRef<any>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleCompile = useCallback(async () => {
    setLoading(true);
    try {
      const response = await axios.post<CompilationResult>('/compile', { code });
      setResult(response.data);
      setActiveTab(response.data.success ? 'ast' : 'errors');
    } catch (requestError) {
      const detail = axios.isAxiosError(requestError) && requestError.response?.data?.detail;
      setResult({
        success: false,
        totalErrors: 1,
        lexicalErrors: 0,
        syntacticErrors: 0,
        semanticErrors: 0,
        errors: [{
          type: 'connection',
          message: typeof detail === 'string' ? detail : 'No fue posible conectar con el analizador en el puerto 8000.',
          line: 0,
          column: 0,
        }],
        tokenCount: 0,
        tokens: [],
        ast: null,
        symbolTable: null,
      });
      setActiveTab('errors');
    } finally {
      setLoading(false);
    }
  }, [code]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
        event.preventDefault();
        handleCompile();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [handleCompile]);

  useEffect(() => {
    const editor = editorRef.current;
    const monaco = monacoRef.current;
    if (!editor || !monaco) return;
    const model = editor.getModel();
    const markers = (result?.errors || []).filter((error) => error.line > 0).map((error) => ({
      startLineNumber: error.line,
      startColumn: error.column + 1,
      endLineNumber: error.line,
      endColumn: Math.max(error.column + 2, model.getLineMaxColumn(error.line)),
      message: error.message,
      severity: monaco.MarkerSeverity.Error,
      source: error.type,
    }));
    monaco.editor.setModelMarkers(model, 'compiscript', markers);
  }, [result]);

  const loadFile = useCallback(async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.cps')) {
      setResult({
        success: false,
        totalErrors: 1,
        lexicalErrors: 0,
        syntacticErrors: 0,
        semanticErrors: 0,
        errors: [{ type: 'connection', message: 'Selecciona un archivo con extensión .cps.', line: 0, column: 0 }],
        tokenCount: 0,
        tokens: [],
        ast: null,
        symbolTable: null,
      });
      setActiveTab('errors');
      return;
    }
    setCode(await file.text());
    setFileName(file.name);
    setResult(null);
  }, []);

  const goToError = (error: CompilationError) => {
    if (error.line < 1 || !editorRef.current) return;
    editorRef.current.setPosition({ lineNumber: error.line, column: error.column + 1 });
    editorRef.current.revealLineInCenter(error.line);
    editorRef.current.focus();
  };

  const configureLanguage = (monaco: any) => {
    monaco.languages.register({ id: 'compiscript' });
    monaco.languages.setMonarchTokensProvider('compiscript', {
      keywords: ['let', 'var', 'const', 'function', 'class', 'new', 'this', 'if', 'else', 'while', 'do', 'for', 'foreach', 'in', 'switch', 'case', 'default', 'try', 'catch', 'break', 'continue', 'return', 'print', 'true', 'false', 'null'],
      typeKeywords: ['integer', 'float', 'string', 'boolean'],
      tokenizer: {
        root: [
          [/[a-zA-Z_]\w*/, { cases: { '@keywords': 'keyword', '@typeKeywords': 'type', '@default': 'identifier' } }],
          [/\d+\.\d+/, 'number.float'], [/\d+/, 'number'],
          [/"([^"\\]|\\.)*$/, 'string.invalid'], [/"/, { token: 'string.quote', bracket: '@open', next: '@string' }],
          [/\/\*/, 'comment', '@comment'], [/\/\/.*$/, 'comment'],
          [/[{}()[\]]/, '@brackets'], [/[<>!=]=?|&&|\|\||[+\-*/%?:.=]/, 'operator'],
        ],
        comment: [[/[^/*]+/, 'comment'], [/\*\//, 'comment', '@pop'], [/[/*]/, 'comment']],
        string: [[/[^\\"]+/, 'string'], [/\\./, 'string.escape'], [/"/, { token: 'string.quote', bracket: '@close', next: '@pop' }]],
      },
    });
  };

  const phaseCards = [
    ['Léxico', result?.lexicalErrors ?? '—', 'lexical'],
    ['Sintáctico', result?.syntacticErrors ?? '—', 'syntactic'],
    ['Semántico', result?.semanticErrors ?? '—', 'semantic'],
  ];

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">C</div>
          <div><strong>Compiscript</strong><span>Analizador estático</span></div>
        </div>
        <div className="topbar-actions">
          <div className="file-pill"><span className="file-status" />{fileName}</div>
          <button className="button button-primary" onClick={handleCompile} disabled={loading}>
            <span className={loading ? 'spinner' : 'play-icon'} aria-hidden="true" />
            {loading ? 'Analizando…' : 'Analizar'}
            {!loading && <kbd>Ctrl ↵</kbd>}
          </button>
        </div>
      </header>

      <section className="workspace">
        <article className={`editor-card ${isDragging ? 'is-dragging' : ''}`}
          onDragOver={(event) => { event.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(event) => { event.preventDefault(); setIsDragging(false); const file = event.dataTransfer.files[0]; if (file) loadFile(file); }}>
          <div className="panel-heading">
            <div><p className="eyebrow">Código fuente</p><h1>{fileName}</h1></div>
            <div className="editor-actions">
              <input ref={fileInputRef} type="file" accept=".cps" hidden onChange={(event) => { const file = event.target.files?.[0]; if (file) loadFile(file); event.target.value = ''; }} />
              <button className="button button-quiet" onClick={() => fileInputRef.current?.click()}>Abrir .cps</button>
              <select aria-label="Cargar ejemplo" defaultValue="" onChange={(event) => {
                const key = event.target.value as keyof typeof examples;
                if (key) { setCode(examples[key]); setFileName(`${key}.cps`); setResult(null); event.target.value = ''; }
              }}>
                <option value="" disabled>Ejemplos</option>
                <option value="factorial">Factorial válido</option>
                <option value="errors">Varios errores</option>
              </select>
            </div>
          </div>
          <div className="editor-wrap">
            {isDragging && <div className="drop-overlay">Suelta aquí tu archivo .cps</div>}
            <Editor
              height="100%"
              language="compiscript"
              value={code}
              beforeMount={configureLanguage}
              onMount={(editor, monaco) => { editorRef.current = editor; monacoRef.current = monaco; }}
              onChange={(value) => setCode(value || '')}
              theme="vs-dark"
              options={{
                minimap: { enabled: false }, fontSize: 14, lineHeight: 23,
                fontFamily: "'Cascadia Code', 'SFMono-Regular', Consolas, monospace",
                padding: { top: 18, bottom: 18 }, scrollBeyondLastLine: false,
                roundedSelection: true, automaticLayout: true, tabSize: 2,
              }}
            />
          </div>
          <footer className="editor-footer"><span>Compiscript · UTF-8</span><span>{code.split('\n').length} líneas</span></footer>
        </article>

        <aside className="analysis-card">
          <div className="analysis-hero">
            <div>
              <p className="eyebrow">Resultado</p>
              <h2>{!result ? 'Listo para analizar' : result.success ? 'Sin errores' : `${result.totalErrors} ${result.totalErrors === 1 ? 'problema' : 'problemas'}`}</h2>
              <p>{!result ? 'Abre un archivo o escribe código para comenzar.' : result.success ? 'Las tres fases finalizaron correctamente.' : 'Revisa los diagnósticos; el análisis continuó tras cada error.'}</p>
            </div>
            <div className={`result-orb ${result ? (result.success ? 'ok' : 'fail') : ''}`}><span>{result ? (result.success ? '✓' : result.totalErrors) : 'C'}</span></div>
          </div>

          <div className="phase-grid">
            {phaseCards.map(([label, value, phase]) => (
              <div className={`phase-card ${phase}`} key={String(label)}><span>{label}</span><strong>{value}</strong></div>
            ))}
          </div>

          <nav className="tabs" aria-label="Resultados del análisis">
            {([
              ['errors', 'Diagnósticos', result?.totalErrors], ['ast', 'Árbol', null],
              ['symbols', 'Símbolos', null], ['tokens', 'Tokens', result?.tokenCount],
            ] as [PanelTab, string, number | null | undefined][]).map(([tab, label, count]) => (
              <button key={tab} className={activeTab === tab ? 'active' : ''} onClick={() => setActiveTab(tab)}>
                {label}{typeof count === 'number' && <span>{count}</span>}
              </button>
            ))}
          </nav>

          <div className="panel-content">
            {!result && <div className="empty-panel"><div className="empty-glyph">{'{ }'}</div><h3>Todo ocurre aquí</h3><p>Los errores, el árbol y los símbolos aparecerán dentro del IDE.</p></div>}

            {result && activeTab === 'errors' && (
              <div className="diagnostics">
                {result.errors.length === 0 && <div className="success-panel"><span>✓</span><div><h3>Programa válido</h3><p>No se encontraron errores léxicos, sintácticos ni semánticos.</p></div></div>}
                {result.errors.map((error, index) => (
                  <button className={`diagnostic ${error.type}`} key={`${error.type}-${error.line}-${index}`} onClick={() => goToError(error)}>
                    <span className="diagnostic-index">{String(index + 1).padStart(2, '0')}</span>
                    <span className="diagnostic-body"><span className="diagnostic-meta">{error.type} {error.line > 0 && `· línea ${error.line}:${error.column + 1}`}</span><strong>{error.message}</strong>{error.context && <code>{error.context}</code>}</span>
                    {error.line > 0 && <span className="diagnostic-arrow">→</span>}
                  </button>
                ))}
              </div>
            )}

            {result && activeTab === 'ast' && (result.ast ? <div className="tree-view"><p className="section-note">Árbol sintáctico generado por ANTLR. Expande cualquier regla para inspeccionarla.</p><AstTree node={result.ast} /></div> : <div className="empty-panel"><h3>Árbol no disponible</h3><p>Corrige los errores críticos del parser e intenta de nuevo.</p></div>)}

            {result && activeTab === 'symbols' && (result.symbolTable ? <div className="scope-view"><p className="section-note">Identificadores organizados según el alcance donde fueron declarados.</p><ScopeTree scope={result.symbolTable} /></div> : <div className="empty-panel"><h3>Sin tabla de símbolos</h3></div>)}

            {result && activeTab === 'tokens' && (
              <div className="token-view">
                <div className="token-header"><span>Tipo</span><span>Lexema</span><span>Posición</span></div>
                {result.tokens.map((token, index) => <div className="token-row" key={`${token.line}-${token.column}-${index}`}><code>{token.type}</code><span>{token.value}</span><small>{token.line}:{token.column + 1}</small></div>)}
                {result.tokens.length === 0 && <div className="empty-panel"><h3>Sin tokens</h3></div>}
              </div>
            )}
          </div>
        </aside>
      </section>
    </main>
  );
}

export default App;
