import React, { useCallback, useEffect, useRef, useState } from 'react';
import axios from 'axios';
import Editor from '@monaco-editor/react';
import './App.css';

// Estos tipos reflejan el JSON que devuelve la API.
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
  intermediateCode?: { text: string; instructions: { op: string }[]; temporaries: { frame: string; created: number; reused: number; peakLive: number }[] } | null;
  diagrams?: Record<string, { url: string; pngUrl: string; path: string }>;
  diagramWarnings?: string[];
}

type PanelTab = 'errors' | 'ast' | 'symbols' | 'tokens' | 'tac';

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

// La imagen completa se puede ampliar y descargar.
function Diagram({ diagram, title }: { diagram?: { url: string; pngUrl: string; path: string }; title: string }) {
  const [zoom, setZoom] = useState(1);
  const [fit, setFit] = useState(true);
  const [naturalWidth, setNaturalWidth] = useState(1000);
  return (
    <div className="diagram-view">
      <div className="diagram-toolbar"><strong>{title}</strong>
        <button className="button button-quiet" onClick={() => { setFit(false); setZoom(Math.max(.25, zoom - .25)); }} aria-label="Reducir diagrama">−</button>
        <button className="button button-quiet" onClick={() => { setFit(false); setZoom(1); }}>{fit ? 'Tamaño real' : `${Math.round(zoom * 100)}%`}</button>
        <button className="button button-quiet" onClick={() => { setFit(false); setZoom(Math.min(4, zoom + .25)); }} aria-label="Ampliar diagrama">+</button>
        <button className="button button-quiet" onClick={() => setFit(true)}>Ajustar</button>
        {diagram && <a className="button button-quiet" href={diagram.pngUrl} download>PNG</a>}
      </div>
      {diagram ? <>
        <p className="section-note">Guardado en {diagram.path}</p>
        <div className="diagram-canvas"><img src={diagram.url} alt={title} onLoad={(event) => setNaturalWidth(event.currentTarget.naturalWidth || 1000)} style={{ width: fit ? '100%' : `${naturalWidth * zoom}px`, maxWidth: 'none' }} /></div>
        <a className="diagram-link" href={diagram.url} target="_blank" rel="noreferrer">Abrir imagen completa ↗</a>
      </> : <div className="empty-panel"><h3>Diagrama no disponible</h3><p>Revisa los avisos del resultado.</p></div>}
    </div>
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
  const revisionRef = useRef(0);
  const requestRef = useRef(0);

  // Envia el texto al backend y guarda los resultados de las tres fases.
  const handleCompile = useCallback(async () => {
    const revision = revisionRef.current;
    const request = ++requestRef.current;
    setLoading(true);
    try {
      const response = await axios.post<CompilationResult>('/compile', { code });
      if (revision !== revisionRef.current || request !== requestRef.current) return;
      setResult(response.data);
      setActiveTab(response.data.success ? 'tac' : 'errors');
    } catch (requestError) {
      if (revision !== revisionRef.current || request !== requestRef.current) return;
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
      // El boton vuelve a habilitarse incluso si falla la conexion.
      if (request === requestRef.current) setLoading(false);
    }
  }, [code]);

  useEffect(() => {
    // El atajo funciona en Windows y macOS y se limpia al desmontar.
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
    // ANTLR cuenta columnas desde cero; Monaco las cuenta desde uno.
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

  // La seleccion y el arrastre usan la misma validacion de archivo.
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
    revisionRef.current += 1;
    setCode(await file.text());
    setFileName(file.name);
    setResult(null);
  }, []);

  // Un clic en el diagnostico enfoca su posicion dentro del editor.
  const goToError = (error: CompilationError) => {
    if (error.line < 1 || !editorRef.current) return;
    editorRef.current.setPosition({ lineNumber: error.line, column: error.column + 1 });
    editorRef.current.revealLineInCenter(error.line);
    editorRef.current.focus();
  };

  // Estas reglas solo colorean el editor; ANTLR hace el analisis real.
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

  // Los contadores resumen cada fase sin ocultar los mensajes individuales.
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
          <div><strong>Los Tres Furiosos 2.0</strong><span>Compiscript · Análisis y TAC</span></div>
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

      {/* El editor y los resultados comparten el espacio principal. */}
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
                if (key) { revisionRef.current += 1; setCode(examples[key]); setFileName(`${key}.cps`); setResult(null); event.target.value = ''; }
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
              onChange={(value) => { revisionRef.current += 1; setCode(value || ''); setResult(null); }}
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
              <p>{!result ? 'Abre un archivo o escribe código para comenzar.' : result.success ? `Análisis completo · ${result.intermediateCode?.instructions.length ?? 0} instrucciones TAC.` : 'Revisa los diagnósticos. No se generó código intermedio.'}</p>
            </div>
            <div className={`result-orb ${result ? (result.success ? 'ok' : 'fail') : ''}`}><span>{result ? (result.success ? '✓' : result.totalErrors) : 'C'}</span></div>
          </div>

          <div className="phase-grid">
            {phaseCards.map(([label, value, phase]) => (
              <div className={`phase-card ${phase}`} key={String(label)}><span>{label}</span><strong>{value}</strong></div>
            ))}
          </div>

          {/* Las pestanas cambian la vista del mismo resultado de analisis. */}
          <nav className="tabs" aria-label="Resultados del análisis">
            {([
              ['errors', 'Diagnósticos', result?.totalErrors], ['ast', 'Árbol', null],
              ['symbols', 'Símbolos', null], ['tac', 'TAC', result?.intermediateCode?.instructions.length], ['tokens', 'Tokens', result?.tokenCount],
            ] as [PanelTab, string, number | null | undefined][]).map(([tab, label, count]) => (
              <button key={tab} className={activeTab === tab ? 'active' : ''} onClick={() => setActiveTab(tab)}>
                {label}{typeof count === 'number' && <span>{count}</span>}
              </button>
            ))}
          </nav>

          <div className="panel-content">
            {result?.diagramWarnings?.map((warning) => <p className="diagram-warning" key={warning}>{warning}</p>)}
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

            {result && activeTab === 'ast' && <Diagram key={`ast-${result.diagrams?.ast?.url}`} diagram={result.diagrams?.ast} title="Árbol sintáctico · ANTLR" />}

            {result && activeTab === 'symbols' && <Diagram key={`symbols-${result.diagrams?.symbols?.url}`} diagram={result.diagrams?.symbols} title="Símbolos y registros de activación" />}

            {result && activeTab === 'tac' && (result.intermediateCode ? <>
              <Diagram key={`tac-${result.diagrams?.tac?.url}`} diagram={result.diagrams?.tac} title="Flujo de control · TAC" />
              <div className="tac-stats">{result.intermediateCode.temporaries.map((pool) => <span key={pool.frame}>{pool.frame}: {pool.created} temporales · {pool.reused} reutilizaciones</span>)}</div>
              <pre className="tac-code">{result.intermediateCode.text}</pre>
            </> : <div className="empty-panel"><h3>TAC bloqueado</h3><p>Corrige todos los errores léxicos, sintácticos y semánticos para generar la representación intermedia.</p></div>)}

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
