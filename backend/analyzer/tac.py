"""Traduce el arbol validado a instrucciones de tres direcciones."""

from dataclasses import dataclass
from grammar.CompiscriptVisitor import CompiscriptVisitor
from analyzer.layout import prepare_layout


@dataclass
class Value:
    name: str
    temporary: bool = False


class TemporaryPool:
    """Reusa un temporal cuando su valor ya fue consumido."""

    def __init__(self):
        self.free = []
        self.live = set()
        self.created = 0
        self.reused = 0
        self.peak = 0

    def acquire(self):
        if self.free:
            name = self.free.pop()
            self.reused += 1
        else:
            self.created += 1
            name = f"t{self.created}"
        self.live.add(name)
        self.peak = max(self.peak, len(self.live))
        return Value(name, True)

    def release(self, value):
        if value and value.temporary and value.name in self.live:
            self.live.remove(value.name)
            self.free.append(value.name)


class TACGenerator(CompiscriptVisitor):
    def __init__(self, analyzer):
        self.analyzer = analyzer
        self.scope = analyzer.symbol_table.global_scope
        self.frames = prepare_layout(analyzer.symbol_table)
        self.instructions = []
        self.pool = TemporaryPool()
        self.pools = []
        self.labels = 0
        self.loops = []
        self.handlers = []
        self.classes = []
        self.functions = []

    def visit(self, ctx):
        if ctx is None:
            return None
        previous = self.scope
        self.scope = getattr(ctx, "_semantic_scope", previous)
        try:
            return super().visit(ctx)
        finally:
            self.scope = previous

    def visitChildren(self, ctx):
        value = None
        for child in ctx.getChildren():
            if hasattr(child, "getRuleIndex"):
                value = self.visit(child)
        return value

    def emit(self, op, a=None, b=None, result=None):
        self.instructions.append({"index": len(self.instructions), "op": op,
                                  "arg1": a, "arg2": b, "result": result,
                                  "handler": self.handlers[-1] if self.handlers else None})

    def label(self):
        self.labels += 1
        return f"L{self.labels}"

    def mark(self, label):
        self.emit("label", result=label)

    def release(self, *values):
        for value in values:
            self.pool.release(value)

    def symbol(self, name):
        symbol = self.scope.lookup_symbol(name)
        if symbol is None and self.classes:
            symbol = self.analyzer._lookup_member(self.classes[-1], name)
        if symbol is None:
            raise ValueError(f"Simbolo sin resolver: {name}")
        return symbol

    def reference(self, name, symbol=None):
        symbol = symbol or self.symbol(name)
        if symbol.symbol_type == "attribute":
            return Value(f"this.{name}")
        if symbol.symbol_type in ("function", "method"):
            output = self.pool.acquire()
            if self.classes and self.analyzer._lookup_member(self.classes[-1], name) is symbol:
                self.emit("bind", "this", name, output.name)
            else:
                self.emit("closure", symbol.storage["label"], symbol.storage["environment"], output.name)
            return output
        return Value(symbol.storage["address"])

    def snapshot(self, value):
        # Conserva el valor antes de una expresion con efectos.
        if value.temporary or value.name in ("true", "false", "null") or value.name[:1].isdigit() or value.name.startswith('"'):
            return value
        output = self.pool.acquire()
        self.emit("copy", value.name, result=output.name)
        return output

    def generate(self, tree):
        self.emit("begin", self.scope.frame["id"])
        self.visit(tree)
        self.emit("end", self.scope.frame["id"])
        self.finish_pool(self.scope.frame)
        return {"format": "Compiscript TAC v1", "instructions": self.instructions,
                "classes": [{"label": symbol.storage["label"],
                             "base": symbol.base_symbol.storage["label"] if symbol.base_symbol else None,
                             "layout": symbol.storage["objectLayout"]}
                            for symbol in self.analyzer._classes.values()],
                "text": "\n".join(self.format_instruction(i) for i in self.instructions),
                "frames": self.frames, "temporaries": self.pools}

    def finish_pool(self, frame):
        stats = {"frame": frame["id"], "created": self.pool.created,
                 "reused": self.pool.reused, "peakLive": self.pool.peak}
        self.pools.append(stats)
        frame["temporarySlots"] = max(frame["temporarySlots"], self.pool.created)
        frame["temporaryOffset"] = frame["size"]
        frame["size"] += self.pool.created * 8

    @staticmethod
    def format_instruction(i):
        op, a, b, r = i["op"], i["arg1"], i["arg2"], i["result"]
        if op == "label":
            return f"{r}:"
        if op == "copy":
            return f"  {r} = {a}"
        if op == "goto":
            return f"  goto {r}"
        if op in ("if_true", "if_false"):
            return f"  {op} {a} goto {r}"
        if op == "try_begin":
            return f"  try_begin catch {r}"
        if op in ("+", "-", "*", "/", "%", "<", "<=", ">", ">=", "==", "!="):
            return f"  {r} = {a} {op} {b}"
        args = ", ".join(str(x) for x in (a, b) if x is not None)
        return f"  {r + ' = ' if r else ''}{op}{' ' + args if args else ''}"

    def visitVariableDeclaration(self, ctx):
        target = self.reference(ctx.Identifier().getText())
        self.emit("declare", str(self.symbol(ctx.Identifier().getText()).data_type), result=target.name)
        if ctx.initializer():
            value = self.visit(ctx.initializer().expression())
            self.emit("copy", value.name, result=target.name)
            self.release(value)

    def visitConstantDeclaration(self, ctx):
        value = self.visit(ctx.expression())
        self.emit("const", value.name, result=self.reference(ctx.Identifier().getText()).name)
        self.release(value)

    def visitAssignment(self, ctx):
        expressions = ctx.expression()
        if len(expressions) == 1:
            target = self.reference(ctx.Identifier().getText(), getattr(ctx, "_target_symbol", None))
        else:
            owner = self.snapshot(self.visit(expressions[0]))
            target = Value(f"{owner.name}.{ctx.Identifier().getText()}")
        value = self.visit(expressions[-1])
        self.emit("copy", value.name, result=target.name)
        self.release(value)
        if len(expressions) > 1:
            self.release(owner)

    def visitAssignExpr(self, ctx):
        target, held = self.lvalue(ctx.lhs)
        value = self.snapshot(self.visit(ctx.assignmentExpr()))
        self.emit("copy", value.name, result=target)
        self.release(*held)
        return value

    def visitPropertyAssignExpr(self, ctx):
        owner = self.snapshot(self.visit(ctx.lhs))
        value = self.snapshot(self.visit(ctx.assignmentExpr()))
        self.emit("copy", value.name, result=f"{owner.name}.{ctx.Identifier().getText()}")
        self.release(owner)
        return value

    def lvalue(self, ctx):
        suffixes = ctx.suffixOp()
        if not suffixes:
            return self.reference(ctx.primaryAtom().getText(), getattr(ctx, "_resolved_symbol", None)).name, []
        owner = self.snapshot(self.left_hand_side(ctx, suffixes[:-1]))
        last = suffixes[-1]
        if type(last).__name__ == "IndexExprContext":
            index = self.snapshot(self.visit(last.expression()))
            return f"{owner.name}[{index.name}]", [owner, index]
        return f"{owner.name}.{last.Identifier().getText()}", [owner]

    def visitExpressionStatement(self, ctx):
        self.release(self.visit(ctx.expression()))

    def visitPrintStatement(self, ctx):
        value = self.visit(ctx.expression())
        self.emit("print", value.name)
        self.release(value)

    def visitIdentifierExpr(self, ctx):
        return self.reference(ctx.Identifier().getText(), getattr(ctx, "_resolved_symbol", None))

    def visitThisExpr(self, ctx):
        return Value("this")

    def visitLiteralExpr(self, ctx):
        return self.visit(ctx.arrayLiteral()) if ctx.arrayLiteral() else Value(ctx.getText())

    def visitPrimaryExpr(self, ctx):
        return self.visit(ctx.literalExpr() or ctx.leftHandSide() or ctx.expression())

    def visitUnaryExpr(self, ctx):
        if ctx.primaryExpr():
            return self.visit(ctx.primaryExpr())
        value = self.visit(ctx.unaryExpr())
        output = self.pool.acquire()
        self.emit("neg" if ctx.getChild(0).getText() == "-" else "not", value.name, result=output.name)
        self.release(value)
        return output

    def binary(self, ctx):
        value = self.visit(ctx.getChild(0))
        for index in range(1, ctx.getChildCount(), 2):
            value = self.snapshot(value)
            other = self.visit(ctx.getChild(index + 1))
            output = self.pool.acquire()
            self.emit(ctx.getChild(index).getText(), value.name, other.name, output.name)
            self.release(value, other)
            value = output
        return value

    visitAdditiveExpr = binary
    visitMultiplicativeExpr = binary
    visitEqualityExpr = binary
    visitRelationalExpr = binary

    def logical(self, ctx, short_value):
        value = self.visit(ctx.getChild(0))
        if ctx.getChildCount() == 1:
            return value
        output = self.pool.acquire()
        done = self.label()
        self.emit("copy", short_value, result=output.name)
        for index in range(0, ctx.getChildCount(), 2):
            if index:
                value = self.visit(ctx.getChild(index))
            self.emit("if_true" if short_value == "true" else "if_false", value.name, result=done)
            self.release(value)
        self.emit("copy", "false" if short_value == "true" else "true", result=output.name)
        self.mark(done)
        return output

    def visitLogicalOrExpr(self, ctx):
        return self.logical(ctx, "true")

    def visitLogicalAndExpr(self, ctx):
        return self.logical(ctx, "false")

    def visitTernaryExpr(self, ctx):
        condition = self.visit(ctx.logicalOrExpr())
        if not ctx.expression():
            return condition
        other, done = self.label(), self.label()
        output = self.pool.acquire()
        self.emit("if_false", condition.name, result=other)
        self.release(condition)
        value = self.visit(ctx.expression(0))
        self.emit("copy", value.name, result=output.name)
        self.release(value)
        self.emit("goto", result=done)
        self.mark(other)
        value = self.visit(ctx.expression(1))
        self.emit("copy", value.name, result=output.name)
        self.release(value)
        self.mark(done)
        return output

    def arguments(self, ctx):
        # Se evaluan todos antes de preparar la llamada externa.
        return [self.snapshot(self.visit(e)) for e in ctx.expression()] if ctx else []

    def call(self, target, arguments, op="call"):
        for argument in arguments:
            self.emit("param", argument.name)
        output = self.pool.acquire()
        self.emit(op, target.name, str(len(arguments)), output.name)
        self.release(target, *arguments)
        return output

    def visitLeftHandSide(self, ctx):
        return self.left_hand_side(ctx, ctx.suffixOp())

    def left_hand_side(self, ctx, suffixes):
        value = self.visit(ctx.primaryAtom())
        for suffix in suffixes:
            kind = type(suffix).__name__
            value = self.snapshot(value)
            if kind == "CallExprContext":
                value = self.call(value, self.arguments(suffix.arguments()))
                continue
            output = self.pool.acquire()
            if kind == "IndexExprContext":
                index = self.visit(suffix.expression())
                self.emit("load_index", value.name, index.name, output.name)
                self.release(index)
            else:
                self.emit("member", value.name, suffix.Identifier().getText(), output.name)
            self.release(value)
            value = output
        return value

    def visitArrayLiteral(self, ctx):
        output = self.pool.acquire()
        self.emit("array", str(len(ctx.expression())), result=output.name)
        for index, expression in enumerate(ctx.expression()):
            value = self.visit(expression)
            self.emit("copy", value.name, result=f"{output.name}[{index}]")
            self.release(value)
        return output

    def visitNewExpr(self, ctx):
        symbol = getattr(ctx, "_class_symbol", None) or self.symbol(ctx.Identifier().getText())
        args = self.arguments(ctx.arguments())
        output = self.pool.acquire()
        self.emit("new", symbol.storage["label"], result=output.name)
        self.emit("init_object", output.name, symbol.storage["label"])
        constructor = self.analyzer._lookup_member(symbol, "constructor")
        if constructor:
            bound = self.pool.acquire()
            self.emit("bind", output.name, "constructor", bound.name)
            returned = self.call(bound, args)
            self.release(returned)
        else:
            self.release(*args)
        return output

    def visitIfStatement(self, ctx):
        other, done = self.label(), self.label()
        value = self.visit(ctx.expression())
        self.emit("if_false", value.name, result=other)
        self.release(value)
        self.visit(ctx.block(0))
        self.emit("goto", result=done)
        self.mark(other)
        if len(ctx.block()) > 1:
            self.visit(ctx.block(1))
        self.mark(done)

    def loop(self, ctx, do_first=False, init=None, update=None, condition=None):
        head, step, done = self.label(), self.label(), self.label()
        if init:
            self.visit(init)
        self.mark(head)
        if not do_first and condition:
            value = self.visit(condition)
            self.emit("if_false", value.name, result=done)
            self.release(value)
        self.loops.append((done, step, len(self.handlers)))
        self.visit(ctx.block())
        self.loops.pop()
        self.mark(step)
        if update:
            self.release(self.visit(update))
        if do_first:
            value = self.visit(condition)
            self.emit("if_true", value.name, result=head)
            self.release(value)
        else:
            self.emit("goto", result=head)
        self.mark(done)

    def visitWhileStatement(self, ctx):
        self.loop(ctx, condition=ctx.expression())

    def visitDoWhileStatement(self, ctx):
        self.loop(ctx, do_first=True, condition=ctx.expression())

    def visitForStatement(self, ctx):
        boundary = max(child.symbol.tokenIndex for child in ctx.children
                       if hasattr(child, "symbol") and child.getText() == ";")
        condition = next((e for e in ctx.expression() if e.start.tokenIndex < boundary), None)
        update = next((e for e in ctx.expression() if e.start.tokenIndex > boundary), None)
        self.loop(ctx, init=ctx.variableDeclaration() or ctx.assignment(), condition=condition, update=update)

    def visitForeachStatement(self, ctx):
        collection = self.snapshot(self.visit(ctx.expression()))
        index, length, test = self.pool.acquire(), self.pool.acquire(), self.pool.acquire()
        head, step, done = self.label(), self.label(), self.label()
        self.emit("copy", "0", result=index.name)
        self.emit("length", collection.name, result=length.name)
        self.mark(head)
        self.emit("<", index.name, length.name, test.name)
        self.emit("if_false", test.name, result=done)
        self.emit("load_index", collection.name, index.name, self.reference(ctx.Identifier().getText()).name)
        self.loops.append((done, step, len(self.handlers)))
        self.visit(ctx.block())
        self.loops.pop()
        self.mark(step)
        self.emit("+", index.name, "1", index.name)
        self.emit("goto", result=head)
        self.mark(done)
        self.release(collection, index, length, test)

    def unwind(self, depth):
        for _ in self.handlers[depth:]:
            self.emit("try_end")

    def visitBreakStatement(self, ctx):
        target, _, depth = self.loops[-1]
        self.unwind(depth)
        self.emit("goto", result=target)

    def visitContinueStatement(self, ctx):
        _, target, depth = next(loop for loop in reversed(self.loops) if loop[1] is not None)
        self.unwind(depth)
        self.emit("goto", result=target)

    def visitReturnStatement(self, ctx):
        value = self.visit(ctx.expression()) if ctx.expression() else None
        self.unwind(0)
        self.emit("return", value.name if value else None)
        self.release(value)

    def visitSwitchStatement(self, ctx):
        value = self.snapshot(self.visit(ctx.expression()))
        done = self.label()
        labels = [self.label() for _ in ctx.switchCase()]
        default = self.label() if ctx.defaultCase() else done
        for case, label in zip(ctx.switchCase(), labels):
            other = self.visit(case.expression())
            test = self.pool.acquire()
            self.emit("==", value.name, other.name, test.name)
            self.emit("if_true", test.name, result=label)
            self.release(other, test)
        self.emit("goto", result=default)
        self.release(value)
        self.loops.append((done, None, len(self.handlers)))
        for case, label in zip(ctx.switchCase(), labels):
            self.mark(label)
            for statement in case.statement():
                self.visit(statement)
        if ctx.defaultCase():
            self.mark(default)
            for statement in ctx.defaultCase().statement():
                self.visit(statement)
        self.loops.pop()
        self.mark(done)

    def visitTryCatchStatement(self, ctx):
        catch, done = self.label(), self.label()
        self.emit("try_begin", result=catch)
        self.handlers.append(catch)
        self.visit(ctx.block(0))
        self.handlers.pop()
        self.emit("try_end")
        self.emit("goto", result=done)
        self.mark(catch)
        self.emit("catch", result=self.reference(ctx.Identifier().getText()).name)
        self.visit(ctx.block(1))
        self.mark(done)

    def visitFunctionDeclaration(self, ctx):
        symbol = self.analyzer._declaration_symbols[id(ctx)]
        skip = self.label()
        self.emit("goto", result=skip)
        self.mark(symbol.storage["label"])
        self.emit("begin", self.scope.frame["id"])
        saved = self.pool, self.loops, self.handlers
        self.pool, self.loops, self.handlers = TemporaryPool(), [], []
        for index, (name, _) in enumerate(symbol.parameters):
            self.emit("receive", str(index), result=self.reference(name).name)
        self.visit(ctx.block())
        self.emit("return")
        self.finish_pool(self.scope.frame)
        self.pool, self.loops, self.handlers = saved
        self.emit("end", self.scope.frame["id"])
        self.mark(skip)

    def visitClassDeclaration(self, ctx):
        symbol = self.analyzer._declaration_symbols[id(ctx)]
        self.classes.append(symbol)
        self.emit("class", symbol.base_symbol.storage["label"] if symbol.base_symbol else None,
                  result=symbol.storage["label"])
        for name, member in symbol.attributes.items():
            if member.symbol_type in ("function", "method"):
                self.emit("method", name, member.storage["label"], symbol.storage["label"])
        skip = self.label()
        self.emit("goto", result=skip)
        self.mark(symbol.storage["label"] + ".init")
        self.emit("begin", self.scope.frame["id"])
        saved = self.pool
        self.pool = TemporaryPool()
        if symbol.base_symbol:
            self.emit("init_object", "this", symbol.base_symbol.storage["label"])
        for member in ctx.classMember():
            if not member.functionDeclaration():
                self.visit(member)
        self.emit("return")
        self.finish_pool(self.scope.frame)
        self.pool = saved
        self.emit("end", self.scope.frame["id"])
        self.mark(skip)
        for member in ctx.classMember():
            if member.functionDeclaration():
                self.visit(member.functionDeclaration())
        self.classes.pop()
