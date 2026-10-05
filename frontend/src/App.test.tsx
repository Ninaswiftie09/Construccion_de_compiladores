import React, { act } from 'react';
import { createRoot, Root } from 'react-dom/client';
import axios from 'axios';
import App from './App';

jest.mock('axios');
jest.mock('@monaco-editor/react', () => ({
  __esModule: true,
  default: ({ value, onChange }: any) => <textarea aria-label="Editor Compiscript" value={value} onChange={(event) => onChange(event.target.value)} />,
}));

const mockedAxios = axios as jest.Mocked<typeof axios>;
const valid = {
  success: true, totalErrors: 0, lexicalErrors: 0, syntacticErrors: 0, semanticErrors: 0,
  errors: [], tokenCount: 1, tokens: [], ast: null, symbolTable: null,
  intermediateCode: { text: '  t1 = 1 + 2', instructions: [{ op: '+' }], temporaries: [{ frame: 's1', created: 1, reused: 2, peakLive: 1 }] },
  diagrams: { tac: { url: '/diagrams/test/tac.svg', pngUrl: '/diagrams/test/tac.png', path: 'output/diagrams/test/tac.png' }, ast: { url: '/diagrams/test/ast.svg', pngUrl: '/diagrams/test/ast.png', path: 'output/diagrams/test/ast.png' } },
  diagramWarnings: [],
};

let container: HTMLDivElement;
let root: Root;

beforeEach(() => {
  (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  act(() => root.render(<App />));
  mockedAxios.post.mockReset();
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
});

function button(text: string) {
  const match = Array.from(container.querySelectorAll('button')).find((node) => node.textContent?.includes(text));
  if (!match) throw new Error(`Boton ausente: ${text}`);
  return match;
}

async function compile(payload: any) {
  mockedAxios.post.mockResolvedValueOnce({ data: payload });
  await act(async () => button('Analizar').click());
}

test('shows image preview, saved path, PNG download and TAC inside IDE', async () => {
  await compile(valid);
  expect(container.querySelector('img')?.getAttribute('src')).toBe(valid.diagrams.tac.url);
  expect(container.textContent).toContain(valid.diagrams.tac.path);
  expect(container.querySelector('a[download]')?.getAttribute('href')).toBe(valid.diagrams.tac.pngUrl);
  expect(container.querySelector('pre')?.textContent).toContain('t1 = 1 + 2');
  expect(container.querySelector('details')).toBeNull();
  act(() => button('+').click());
  expect(container.querySelector('img')?.style.width).toBe('1250px');
  act(() => button('Ajustar').click());
  expect(container.querySelector('img')?.style.width).toBe('100%');
  act(() => button('Árbol').click());
  expect(container.querySelector('img')?.getAttribute('src')).toBe(valid.diagrams.ast.url);
});

test('shows all diagnostics and blocks TAC for invalid source', async () => {
  await compile({ ...valid, success: false, totalErrors: 2, intermediateCode: null, diagrams: {}, errors: [
    { type: 'semantic', message: 'Variable ausente', line: 1, column: 0 },
    { type: 'syntactic', message: 'Falta expresión', line: 2, column: 0 },
  ] });
  expect(container.textContent).toContain('Variable ausente');
  expect(container.textContent).toContain('Falta expresión');
  act(() => button('TAC').click());
  expect(container.textContent).toContain('TAC bloqueado');
  expect(container.querySelector('img')).toBeNull();
});

test('loads a cps file selected through the UI and sends its text', async () => {
  const input = container.querySelector('input[type=file]') as HTMLInputElement;
  Object.defineProperty(input, 'files', { value: [{ name: 'demo.cps', text: async () => 'let x = 3;' }], configurable: true });
  await act(async () => input.dispatchEvent(new Event('change', { bubbles: true })));
  expect(container.querySelector('textarea')?.value).toBe('let x = 3;');
  await compile(valid);
  expect(mockedAxios.post).toHaveBeenCalledWith('/compile', { code: 'let x = 3;' });
});

test('does not show a stale result after the user changes source', async () => {
  let complete: (value: any) => void = () => {};
  mockedAxios.post.mockImplementationOnce(() => new Promise((resolve) => { complete = resolve; }));
  act(() => button('Analizar').click());
  const select = container.querySelector('select') as HTMLSelectElement;
  act(() => { select.value = 'errors'; select.dispatchEvent(new Event('change', { bubbles: true })); });
  await act(async () => complete({ data: valid }));
  expect(container.textContent).toContain('Listo para analizar');
  expect(container.querySelector('img')).toBeNull();
});
