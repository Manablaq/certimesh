#!/usr/bin/env python3
"""Build a behavior-identical compact source artifact for Bradbury deployment.

GenLayer stores intelligent-contract source in deployment calldata. The
canonical source stays reviewer-friendly; this artifact removes comments and
docstrings, shortens internal names, and is accepted only after an
ABI-preserving executable-AST proof.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import io
import keyword
from pathlib import Path
import re
import tokenize

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "contracts/certimesh_program_registry.py"
DEPLOY = ROOT / "contracts/certimesh_program_registry_deploy.py"
DEPENDS = '# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }\n'


class StripDocstrings(ast.NodeTransformer):
    @staticmethod
    def strip(node):
        body = getattr(node, "body", None)
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            node.body = body[1:]
        return node

    def visit_Module(self, node):
        self.generic_visit(node)
        return self.strip(node)

    def visit_ClassDef(self, node):
        self.generic_visit(node)
        return self.strip(node)

    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        return self.strip(node)


class StripPrivateAnnotations(ast.NodeTransformer):
    """Remove annotations that cannot affect the deployed public ABI.

    GenVM derives the contract ABI from public methods and storage/dataclass
    declarations.  Module helpers and private contract methods are internal
    implementation details; dropping only their annotations reduces calldata
    without changing the callable surface or storage schema.
    """

    def __init__(self):
        self.class_stack: list[str] = []

    def visit_ClassDef(self, node):
        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()
        return node

    def visit_FunctionDef(self, node):
        internal = not self.class_stack or (
            self.class_stack[-1] == "CertiMeshProgramRegistry"
            and node.name.startswith("_")
            and not node.name.startswith("__")
        )
        if internal:
            for argument in (
                *node.args.posonlyargs,
                *node.args.args,
                *node.args.kwonlyargs,
            ):
                argument.annotation = None
            if node.args.vararg:
                node.args.vararg.annotation = None
            if node.args.kwarg:
                node.args.kwarg.annotation = None
            node.returns = None
        self.generic_visit(node)
        return node

    visit_AsyncFunctionDef = visit_FunctionDef

def executable_tree(source: str) -> ast.AST:
    tree = StripDocstrings().visit(ast.parse(source))
    ast.fix_missing_locations(tree)
    return tree


def transport_tree(source: str) -> ast.AST:
    tree = executable_tree(source)
    tree = StripPrivateAnnotations().visit(tree)
    ast.fix_missing_locations(tree)
    return tree


def compact_indentation(source: str) -> str:
    lines = []
    for line in source.splitlines():
        spaces = len(line) - len(line.lstrip(" "))
        if spaces % 4 == 0:
            line = "\t" * (spaces // 4) + line[spaces:]
        lines.append(line.rstrip())
    return "\n".join(lines) + "\n"


def lexical_minify_line(line: str) -> str:
    prefix_len = len(line) - len(line.lstrip(" \t"))
    prefix, body = line[:prefix_len], line[prefix_len:]
    if not body or body.lstrip().startswith("#"):
        return line.rstrip()
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(body + "\n").readline))
    except (tokenize.TokenError, IndentationError):
        return line.rstrip()
    # Keep f-string source intact.  Python 3.12 exposes the interior as
    # token fragments; rebuilding it token-by-token can change literal text
    # inside the string even when the resulting file still parses.
    if hasattr(tokenize, "FSTRING_START") and any(
        token.type == tokenize.FSTRING_START for token in tokens
    ):
        return line.rstrip()
    ignored = {tokenize.ENDMARKER, tokenize.NEWLINE, tokenize.NL, tokenize.INDENT, tokenize.DEDENT, tokenize.COMMENT}
    # Python 3.12 tokenizes f-strings as a sequence beginning with
    # FSTRING_START rather than as a single STRING token.  Treat the start
    # marker as a word so `return f"..."` cannot collapse into `returnf"..."`.
    word_types = {tokenize.NAME, tokenize.NUMBER, tokenize.STRING}
    if hasattr(tokenize, "FSTRING_START"):
        word_types.add(tokenize.FSTRING_START)
    output = ""
    previous = None
    for token in tokens:
        if token.type in ignored:
            continue
        text = token.string
        need_space = False
        if previous is not None:
            previous_type, previous_text = previous
            need_space = previous_type in word_types and token.type in word_types
            need_space = need_space or (previous_type == tokenize.NUMBER and text.startswith("."))
            need_space = need_space or (previous_text.endswith(".") and token.type == tokenize.NUMBER)
        output += (" " if need_space else "") + text
        previous = (token.type, text)
    return prefix + output


def ast_dump(tree: ast.AST) -> str:
    return ast.dump(tree, include_attributes=False)


def lexical_minify(source: str, expected: str) -> str:
    candidate = "\n".join(lexical_minify_line(line) for line in source.splitlines() if line.strip()) + "\n"
    if ast_dump(ast.parse(candidate)) != expected:
        raise SystemExit("STOP: lexical compaction changed executable AST")
    return candidate


def collapse_single_statement_suites(source: str, expected: str) -> str:
    text = source
    changed = True
    while changed:
        changed = False
        lines = text.splitlines()
        output = []
        index = 0
        while index < len(lines):
            line = lines[index]
            indent = len(line) - len(line.lstrip("\t"))
            stripped = line.lstrip("\t")
            if index + 1 < len(lines) and stripped.endswith(":"):
                child = lines[index + 1]
                child_indent = len(child) - len(child.lstrip("\t"))
                child_text = child.lstrip("\t")
                after = index + 2
                only = after >= len(lines) or len(lines[after]) - len(lines[after].lstrip("\t")) <= indent
                if child_indent == indent + 1 and only and child_text and not child_text.endswith(":") and not child_text.startswith("@"):
                    candidate = "\n".join(output + [line + child_text] + lines[index + 2:]) + "\n"
                    try:
                        if ast_dump(ast.parse(candidate)) == expected:
                            output.append(line + child_text)
                            index += 2
                            changed = True
                            continue
                    except SyntaxError:
                        pass
            output.append(line)
            index += 1
        text = "\n".join(output) + "\n"
    return text


def pack_same_indent_statements(source: str, expected: str) -> str:
    lines = source.splitlines()
    index = 0
    while index < len(lines) - 1:
        left, right = lines[index], lines[index + 1]
        left_prefix = re.match(r"^[\t ]*", left).group(0)
        right_prefix = re.match(r"^[\t ]*", right).group(0)
        if left_prefix and left_prefix == right_prefix:
            merged = left + ";" + right[len(right_prefix):]
            trial = "\n".join(lines[:index] + [merged] + lines[index + 2:]) + "\n"
            try:
                if ast_dump(ast.parse(trial)) == expected:
                    lines[index] = merged
                    del lines[index + 1]
                    continue
            except SyntaxError:
                pass
        index += 1
    result = "\n".join(lines) + "\n"
    if ast_dump(ast.parse(result)) != expected:
        raise SystemExit("STOP: statement packing changed executable AST")
    return result


def module_bindings(tree: ast.AST) -> set[str]:
    result = set()
    for node in getattr(tree, "body", []):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            result.add(node.name)
        elif isinstance(node, ast.Assign):
            result.update(target.id for target in node.targets if isinstance(target, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            result.add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            result.update(alias.asname or alias.name.split(".")[0] for alias in node.names)
    return result


def symbol_maps(tree: ast.AST) -> tuple[dict[str, str], dict[str, str]]:
    bindings = module_bindings(tree)
    globals_to_shorten = sorted(
        (name for name in bindings if (name.startswith("_") and not name.startswith("__")) or name.isupper()),
        key=lambda name: (-len(name), name),
    )
    global_map = {name: f"G{index}" for index, name in enumerate(globals_to_shorten)}
    contract = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "CertiMeshProgramRegistry")
    private_methods = sorted(
        (node.name for node in contract.body if isinstance(node, ast.FunctionDef) and node.name.startswith("_") and not node.name.startswith("__")),
        key=lambda name: (-len(name), name),
    )
    method_map = {name: f"m{index}" for index, name in enumerate(private_methods)}
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    attrs = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    if set(global_map.values()) & names or set(method_map.values()) & attrs:
        raise SystemExit("STOP: private symbol compaction collision")
    if any(keyword.iskeyword(name) for name in (*global_map.values(), *method_map.values())):
        raise SystemExit("STOP: generated private symbol is a Python keyword")
    return global_map, method_map


class RenameInternalSymbols(ast.NodeTransformer):
    def __init__(self, global_map, method_map, reverse=False):
        self.global_map = {value: key for key, value in global_map.items()} if reverse else global_map
        self.method_map = {value: key for key, value in method_map.items()} if reverse else method_map
        self.class_stack = []

    def visit_Name(self, node):
        node.id = self.global_map.get(node.id, node.id)
        return node

    def visit_Attribute(self, node):
        self.generic_visit(node)
        node.attr = self.method_map.get(node.attr, node.attr)
        return node

    def visit_FunctionDef(self, node):
        if not self.class_stack:
            node.name = self.global_map.get(node.name, node.name)
        elif self.class_stack[-1] == "CertiMeshProgramRegistry":
            node.name = self.method_map.get(node.name, node.name)
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node):
        return self.visit_FunctionDef(node)

    def visit_ClassDef(self, node):
        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()
        return node


def local_map(node: ast.FunctionDef, public: bool) -> dict[str, str]:
    nested = any(
        child is not node and isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
        for child in ast.walk(node)
    )
    if nested:
        return {}
    bound = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and isinstance(child.ctx, (ast.Store, ast.Del)):
            bound.add(child.id)
        elif isinstance(child, ast.arg):
            bound.add(child.arg)
        elif isinstance(child, ast.ExceptHandler) and child.name:
            bound.add(child.name)
    protected = {"self"}
    if public:
        protected.update(arg.arg for arg in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs))
    used = {child.id for child in ast.walk(node) if isinstance(child, ast.Name)}
    candidates = list("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ") + [f"v{i}" for i in range(1000)]
    result = {}
    for name in sorted(bound - protected, key=lambda value: (-len(value), value)):
        for candidate in candidates:
            if candidate not in used and candidate not in result.values() and not keyword.iskeyword(candidate):
                result[name] = candidate
                used.add(candidate)
                break
    return result


class RenameLocalNames(ast.NodeTransformer):
    def __init__(self, maps=None, reverse=False):
        self.maps = maps if maps is not None else []
        self.reverse = reverse
        self.index = 0
        self.current = {}

    def visit_Name(self, node):
        node.id = self.current.get(node.id, node.id)
        return node

    def visit_ExceptHandler(self, node):
        self.generic_visit(node)
        if node.name:
            node.name = self.current.get(node.name, node.name)
        return node

    def process(self, node):
        mapping = self.maps[self.index] if self.reverse else local_map(node, any("gl.public" in ast.unparse(dec) for dec in node.decorator_list))
        self.index += 1
        if not self.reverse:
            self.maps.append(mapping)
        else:
            mapping = {value: key for key, value in mapping.items()}
        previous = self.current
        self.current = mapping
        for arg in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs):
            arg.arg = mapping.get(arg.arg, arg.arg)
        if node.args.vararg:
            node.args.vararg.arg = mapping.get(node.args.vararg.arg, node.args.vararg.arg)
        if node.args.kwarg:
            node.args.kwarg.arg = mapping.get(node.args.kwarg.arg, node.args.kwarg.arg)
        node.body = [self.visit(statement) for statement in node.body]
        self.current = previous
        return node

    def visit_FunctionDef(self, node):
        return self.process(node)

    def visit_AsyncFunctionDef(self, node):
        return self.process(node)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    canonical_bytes = CANONICAL.read_bytes()
    tree = transport_tree(canonical_bytes.decode("utf-8"))
    expected = ast_dump(tree)
    global_map, method_map = symbol_maps(tree)
    compact_tree = RenameInternalSymbols(global_map, method_map).visit(copy.deepcopy(tree))
    ast.fix_missing_locations(compact_tree)
    local_maps = []
    compact_tree = RenameLocalNames(local_maps).visit(compact_tree)
    ast.fix_missing_locations(compact_tree)
    body = compact_indentation(ast.unparse(compact_tree))
    expected_compact = ast_dump(compact_tree)
    body = lexical_minify(DEPENDS + body, expected_compact)
    body = collapse_single_statement_suites(body, expected_compact)
    output = pack_same_indent_statements(body, expected_compact).encode("utf-8")
    parsed = ast.parse(output.decode("utf-8"))
    restored = RenameLocalNames(local_maps, reverse=True).visit(copy.deepcopy(parsed))
    restored = RenameInternalSymbols(global_map, method_map, reverse=True).visit(restored)
    ast.fix_missing_locations(restored)
    if ast_dump(restored) != expected:
        raise SystemExit("STOP: deployment artifact failed reversible executable-AST proof")
    DEPLOY.write_bytes(output)
    print(f"CANONICAL_BYTES={len(canonical_bytes)}")
    print(f"DEPLOY_BYTES={len(output)}")
    print(f"CANONICAL_SHA256={digest(canonical_bytes)}")
    print(f"DEPLOY_SHA256={digest(output)}")
    print("PASS deployment artifact is executable-AST equivalent")


if __name__ == "__main__":
    main()
