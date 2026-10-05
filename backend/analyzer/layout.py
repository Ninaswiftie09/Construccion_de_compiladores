"""Direcciones simbolicas y registros de activacion del TAC."""


def prepare_layout(table):
    frames = []
    classes = []
    counter = 0

    def walk(scope, frame=None):
        nonlocal counter
        counter += 1
        scope.storage_id = f"s{counter}"
        if scope.scope_type in ("global", "function", "class"):
            parent_frame = frame
            frame = {
                "id": scope.storage_id, "name": scope.name or scope.scope_type,
                "kind": scope.scope_type, "lexicalParent": parent_frame["id"] if parent_frame else None,
                "header": {"returnAddress": 0, "dynamicLink": 8, "staticLink": 16, "receiver": 24},
                "slots": [], "size": 32, "temporarySlots": 0,
            }
            frames.append(frame)
            scope.activation_record = frame
        scope.frame = frame
        for symbol in scope.symbols.values():
            address = f"{scope.storage_id}.{symbol.name}"
            if symbol.symbol_type in ("function", "method", "class"):
                symbol.storage = {"address": address, "label": address, "kind": symbol.symbol_type,
                                  "environment": frame["id"]}
                if symbol.symbol_type == "class":
                    classes.append(symbol)
            else:
                slot = {"address": address, "name": symbol.name, "offset": frame["size"],
                        "size": 8, "type": str(symbol.data_type), "kind": symbol.symbol_type}
                symbol.storage = {**slot, "frame": frame["id"]}
                frame["slots"].append(slot)
                frame["size"] += 8
        for child in scope.child_scopes:
            walk(child, frame)

    walk(table.global_scope)

    def object_layout(symbol):
        if "objectLayout" in symbol.storage:
            return symbol.storage["objectLayout"]
        parent = object_layout(symbol.base_symbol) if symbol.base_symbol else {"fields": [], "methods": {}}
        fields = [dict(field) for field in parent["fields"]]
        methods = dict(parent["methods"])
        for name, member in symbol.attributes.items():
            if member.symbol_type == "method":
                methods[name] = member.storage["label"]
            else:
                previous = next((field for field in fields if field["name"] == name), None)
                offset = previous["offset"] if previous else 8 + len(fields) * 8
                field = {"name": name, "offset": offset, "type": str(member.data_type)}
                member.storage["objectOffset"] = offset
                if previous:
                    fields[fields.index(previous)] = field
                else:
                    fields.append(field)
        layout = {"size": 8 + len(fields) * 8, "header": {"classDescriptor": 0},
                  "fields": fields, "methods": methods}
        symbol.storage["objectLayout"] = layout
        return layout

    for symbol in classes:
        object_layout(symbol)
    return frames
