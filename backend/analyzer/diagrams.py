"""Guarda diagramas reales del arbol, los simbolos y el TAC."""

import json
import subprocess
import uuid
from pathlib import Path
from analyzer.tac import TACGenerator


OUTPUT_DIR = Path(__file__).resolve().parents[2] / "output" / "diagrams"


class Graph:
    def __init__(self, direction="TB"):
        self.lines = ["digraph G {", f"rankdir={direction};", 'bgcolor="#0f1217";',
                      'node [shape=box, style="rounded,filled", fillcolor="#1d2930", color="#7ef0c2", fontcolor="#f3f5f7", fontname="Consolas", fontsize=11];',
                      'edge [color="#8996a5", fontcolor="#b8c5d2", fontname="Consolas", fontsize=10];']
        self.count = 0

    def node(self, text):
        name = f"n{self.count}"
        self.count += 1
        self.lines.append(f"{name} [label={json.dumps(text, ensure_ascii=False)}];")
        return name

    def edge(self, a, b, label=""):
        self.lines.append(f"{a} -> {b} [label={json.dumps(label)}];")

    def source(self):
        return "\n".join(self.lines + ["}"])


def ast_graph(root):
    graph = Graph()

    def walk(node):
        name = graph.node(node["text"] if node["name"] == "token" else node["name"])
        for child in node["children"]:
            graph.edge(name, walk(child))
        return name

    walk(root)
    return graph


def symbol_graph(root):
    graph = Graph()

    def walk(scope):
        frame = scope.get("activationRecord") or {}
        title = f"{scope['name'] or scope['type']} ({scope['type']})"
        if frame:
            title += f"\nFrame {frame['id']} · {frame['size']} bytes · enlace {frame['lexicalParent']}"
        rows = [title]
        for symbol in scope["symbols"]:
            storage = symbol.get("storage") or {}
            rows.append(f"{symbol['name']}: {symbol['dataType']} | {storage.get('address', 'sin layout')} | offset {storage.get('offset', '-')}")
            if "objectOffset" in storage:
                rows.append(f"  campo de objeto: offset {storage['objectOffset']}")
            if "objectLayout" in storage:
                rows.append(f"  objeto: {storage['objectLayout']['size']} bytes | base {symbol.get('baseClass') or '-'}")
        name = graph.node("\n".join(rows))
        for child in scope["children"]:
            graph.edge(name, walk(child), "alcance")
        return name

    walk(root)
    return graph


def control_graph(code):
    # Se separan bloques en etiquetas y despues de cada salto.
    graph = Graph("TB")
    graph.lines.extend(['pack=true;', 'packmode="array_u1";'])
    instructions = code["instructions"]
    leaders = {0}
    for index, instruction in enumerate(instructions):
        if instruction["op"] == "label":
            leaders.add(index)
        if instruction["op"] in ("goto", "if_true", "if_false", "return", "end", "try_begin") and index + 1 < len(instructions):
            leaders.add(index + 1)
    starts = sorted(leaders)
    blocks, targets = [], {}
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(instructions)
        block = instructions[start:end]
        # Omite los cierres sin flujo despues de un retorno.
        if start > 0 and instructions[start - 1]["op"] == "return" and all(
                i["op"] == "end" or (i["op"] == "return" and i["arg1"] is None) for i in block):
            continue
        name = graph.node(f"B{index}\n" + "\n".join(TACGenerator.format_instruction(i) for i in block))
        blocks.append((name, block))
        for instruction in block:
            if instruction["op"] == "label":
                targets[instruction["result"]] = name
    for index, (name, block) in enumerate(blocks):
        last = block[-1]
        op = last["op"]
        if op in ("goto", "if_true", "if_false", "try_begin"):
            graph.edge(name, targets[last["result"]], "excepcion" if op == "try_begin" else "salto")
        if op not in ("goto", "return", "end") and index + 1 < len(blocks):
            graph.edge(name, blocks[index + 1][0], "sigue")
        handlers = {i.get("handler") for i in block if i["op"] in ("call", "load_index", "member", "new", "init_object", "/", "%")}
        for handler in handlers - {None}:
            graph.edge(name, targets[handler], "excepcion")
    return graph


def save_diagrams(result):
    graphs = {}
    if result.ast:
        graphs["ast"] = ast_graph(result.ast)
    if result.symbol_table:
        graphs["symbols"] = symbol_graph(result.symbol_table)
    if result.intermediate_code is not None:
        graphs["tac"] = control_graph(result.intermediate_code)
    folder = OUTPUT_DIR / uuid.uuid4().hex
    folder.mkdir(parents=True, exist_ok=True)
    diagrams, warnings = {}, []
    for kind, graph in graphs.items():
        source = folder / f"{kind}.dot"
        source.write_text(graph.source(), encoding="utf-8")
        try:
            for extension in ("svg", "png"):
                subprocess.run(["dot", f"-T{extension}", str(source), "-o", str(folder / f"{kind}.{extension}")],
                               check=True, capture_output=True, timeout=30)
            diagrams[kind] = {"url": f"/diagrams/{folder.name}/{kind}.svg",
                              "pngUrl": f"/diagrams/{folder.name}/{kind}.png",
                              "path": f"output/diagrams/{folder.name}/{kind}.png"}
        except (OSError, subprocess.SubprocessError):
            warnings.append(f"No se pudo dibujar {kind}. Instala Graphviz y agrega dot al PATH.")
    if result.intermediate_code is not None:
        (folder / "program.tac").write_text(result.intermediate_code["text"], encoding="utf-8")
        (folder / "program.json").write_text(json.dumps(result.intermediate_code, ensure_ascii=False, indent=2), encoding="utf-8")
    return diagrams, warnings
