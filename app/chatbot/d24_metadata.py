"""Read the reviewed D2.4 source as data and compile its answer controls."""

import ast
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path


SOURCE = (
    Path(__file__).resolve().parents[1]
    / "deliverable_2/questionnaires/Dataset_and_evidence.py"
)
MANIFEST = Path(__file__).with_name("d24_compatibility.json")


class D24CompatibilityError(ValueError):
    """The installed owner questionnaire needs a compatibility review."""

    def __init__(self, reason):
        super().__init__(f"D2.4 compatibility manifest requires review. {reason}")


def _unsupported(node):
    return D24CompatibilityError(
        f"Found unsupported {type(node).__name__} "
        f"at owner source line {getattr(node, 'lineno', '?')}."
    )


@dataclass(frozen=True)
class AnswerField:
    prompt: str
    kind: str
    options: tuple = ()

    def check(self, value):
        if self.kind == "text":
            if not isinstance(value, str) or not value.strip():
                raise ValueError("Expected non-empty text.")
        elif self.kind == "select":
            if not isinstance(value, str) or value not in self.options:
                raise ValueError("Expected an allowed option.")
        elif (
            not isinstance(value, list) or not value
            or any(not isinstance(item, str) or item not in self.options for item in value)
            or len(value) != len(set(value))
        ):
            raise ValueError("Expected a non-empty list of distinct allowed options.")


@dataclass(frozen=True)
class _Control:
    field: AnswerField
    default: object
    visible: object = None


@dataclass(frozen=True)
class _Assignment:
    path: tuple
    value: object
    field_id: str | None = None


@dataclass(frozen=True)
class _Branch:
    condition: object
    when_true: tuple
    when_false: tuple


def _path(node):
    if isinstance(node, ast.Name):
        return (node.id,)
    if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
        if isinstance(node.slice.value, str):
            return (*_path(node.value), node.slice.value)
    raise _unsupported(node)


def _read(path, values):
    value = values
    for key in path:
        value = value[key]
    return value


def _write(path, value, values):
    _read(path[:-1], values)[path[-1]] = value


def _expression(node):
    """Compile only the owner's supported predicate operations, without eval."""
    if isinstance(node, ast.Constant):
        return lambda values: node.value
    if isinstance(node, (ast.Name, ast.Subscript)):
        path = _path(node)
        return lambda values: _read(path, values)
    if isinstance(node, ast.List):
        items = [_expression(item) for item in node.elts]
        return lambda values: [item(values) for item in items]
    if isinstance(node, (ast.Tuple, ast.Set, ast.Dict)):
        literal = ast.literal_eval(node)
        return lambda values: deepcopy(literal)
    if isinstance(node, ast.BoolOp):
        operands = [_expression(item) for item in node.values]
        combine = all if isinstance(node.op, ast.And) else any
        return lambda values: combine(operand(values) for operand in operands)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        operand = _expression(node.operand)
        return lambda values: not operand(values)
    if isinstance(node, ast.Compare) and len(node.ops) == 1:
        left, right = _expression(node.left), _expression(node.comparators[0])
        if isinstance(node.ops[0], ast.Eq):
            return lambda values: left(values) == right(values)
        if isinstance(node.ops[0], ast.In):
            return lambda values: left(values) in right(values)
        if isinstance(node.ops[0], ast.NotIn):
            return lambda values: left(values) not in right(values)
    if isinstance(node, ast.Call) and not node.keywords:
        if ast.unparse(node.func) == "any" and len(node.args) == 1:
            generator = node.args[0]
            if isinstance(generator, ast.GeneratorExp) and len(generator.generators) == 1:
                loop = generator.generators[0]
                if isinstance(loop.target, ast.Name) and not loop.ifs and not loop.is_async:
                    test, items = _expression(generator.elt), _expression(loop.iter)
                    return lambda values: any(
                        test({**values, loop.target.id: item}) for item in items(values)
                    )
        if isinstance(node.func, ast.Attribute) and node.func.attr == "issubset":
            base = node.func.value
            if (isinstance(base, ast.Call) and ast.unparse(base.func) == "set"
                    and not base.keywords and len(base.args) == 1 and len(node.args) == 1):
                items, allowed = _expression(base.args[0]), _expression(node.args[0])
                return lambda values: set(items(values)).issubset(allowed(values))
    raise _unsupported(node)


class _Compiler:
    def __init__(self, tree, manifest):
        self.sections = manifest["sections"]
        self.local_paths = manifest["local_answer_paths"]
        functions = {}
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name not in functions and not node.decorator_list:
                functions[node.name] = node
            elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                continue
            elif isinstance(node, ast.Import) and [(alias.name, alias.asname) for alias in node.names] == [
                ("streamlit", "st")
            ]:
                continue
            else:
                raise _unsupported(node)
        self.helpers = {name: node for name, node in functions.items() if name != "render_dataset_evidence"}
        self.renderer = functions["render_dataset_evidence"]
        self.programs = {}

    def compile(self, fingerprint):
        self.programs["gmlp"] = self._block(self.renderer.body, "gmlp")
        if set(self.programs) != {"gmlp", *self.sections}:
            raise D24CompatibilityError("Native record sections changed.")
        return _Metadata(self.sections, self.programs, fingerprint)

    def _block(self, statements, scope):
        program = []
        for node in statements:
            if isinstance(node, ast.If):
                program.append(_Branch(_expression(node.test), self._block(node.body, scope),
                                       self._block(node.orelse, scope)))
            elif isinstance(node, ast.For) and scope == "gmlp":
                if not isinstance(node.target, ast.Name) or node.orelse:
                    raise _unsupported(node)
                append = node.body[-1]
                if not isinstance(append, ast.Expr) or not isinstance(append.value, ast.Call):
                    raise _unsupported(node)
                call = append.value
                path = _path(call.func.value) if isinstance(call.func, ast.Attribute) else ()
                if len(call.args) != 1 or not isinstance(call.args[0], ast.Name):
                    raise _unsupported(node)
                kind = call.args[0].id
                if (kind not in self.sections or kind in self.programs
                        or path != ("profile", self.sections[kind]) or call.func.attr != "append"
                        or ast.unparse(node.iter) != f"range(int({kind}_count))"):
                    raise _unsupported(node)
                self.programs[kind] = self._block(node.body[:-1], kind)
            elif isinstance(node, ast.With) and len(node.items) == 1:
                item = node.items[0]
                call = item.context_expr
                if (not isinstance(call, ast.Call) or ast.unparse(call.func) != "st.expander"
                        or item.optional_vars):
                    raise _unsupported(node)
                program.extend(self._block(node.body, scope))
            elif isinstance(node, ast.Assign) and len(node.targets) == 1:
                path = _path(node.targets[0])
                value = node.value
                if isinstance(value, ast.Call) and ast.unparse(value.func) == "st.number_input":
                    if scope != "gmlp" or path not in {(f"{kind}_count",) for kind in self.sections}:
                        raise _unsupported(node)
                    continue
                if isinstance(value, ast.Call) and ast.unparse(value.func) != "any":
                    field_id = self.local_paths.get(scope, {}).get(path[0]) if len(path) == 1 else ".".join(path[1:])
                    root = "profile" if scope == "gmlp" else scope
                    if not field_id or (len(path) > 1 and path[0] != root):
                        raise _unsupported(node)
                    program.append(_Assignment(path, self._control(value), field_id))
                else:
                    program.append(_Assignment(path, _expression(value)))
            elif isinstance(node, ast.Return) and ast.unparse(node.value) == "profile":
                continue
            elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                if ast.unparse(node.value.func) not in {
                    "st.header", "st.info", "st.write", "st.divider", "st.subheader", "st.markdown",
                }:
                    raise _unsupported(node)
            else:
                raise _unsupported(node)
        return tuple(program)

    def _control(self, call):
        name = ast.unparse(call.func)
        if name in {"st.text_input", "st.selectbox", "st.multiselect"}:
            return self._widget(call, ast.literal_eval(call.args[0]))
        helper = self.helpers.get(name)
        if name not in {"show_details", "show_other", "yes_no_unknown", "yes_partly_no_unknown"} or not helper:
            raise _unsupported(call)
        keywords = {keyword.arg for keyword in call.keywords}
        if len(call.args) != 2 or keywords - ({"height", "placeholder"} if name == "show_details" else set()):
            raise _unsupported(call)
        expected_args = {
            "show_details": ["prompt", "key", "height", "placeholder"],
            "show_other": ["selected", "key", "label"],
            "yes_no_unknown": ["prompt", "key"],
            "yes_partly_no_unknown": ["prompt", "key"],
        }
        signature = helper.args
        if ([arg.arg for arg in signature.args] != expected_args[name]
                or signature.posonlyargs or signature.kwonlyargs or signature.vararg or signature.kwarg
                or ast.get_docstring(helper) is None):
            raise _unsupported(helper)
        body = helper.body[1:]  # Owner helpers begin with a docstring.
        if name == "show_other":
            if len(body) != 2:
                raise _unsupported(helper)
            branch, fallback = body
            if (not isinstance(branch, ast.If) or len(branch.body) != 1 or branch.orelse
                    or not isinstance(branch.body[0], ast.Return)
                    or not isinstance(fallback, ast.Return) or ast.literal_eval(fallback.value) is not None):
                raise _unsupported(helper)
            test, selected = _expression(branch.test), _expression(call.args[0])
            label = ast.literal_eval(helper.args.defaults[0])
            widget = self._helper_widget(branch.body[0].value, "label", label)
            return _Control(widget.field, widget.default, lambda values: test({"selected": selected(values)}))
        if len(body) != 1 or not isinstance(body[0], ast.Return):
            raise _unsupported(helper)
        return self._helper_widget(body[0].value, "prompt", ast.literal_eval(call.args[0]))

    def _helper_widget(self, call, prompt_parameter, prompt):
        if not isinstance(call, ast.Call) or not call.args or ast.unparse(call.args[0]) != prompt_parameter:
            raise _unsupported(call)
        return self._widget(call, prompt)

    @staticmethod
    def _widget(call, prompt):
        if not isinstance(call, ast.Call) or not isinstance(prompt, str):
            raise _unsupported(call)
        kind = ast.unparse(call.func)
        keywords = {keyword.arg for keyword in call.keywords}
        if kind in {"st.text_input", "st.text_area"}:
            if len(call.args) != 1 or keywords - {"key", "placeholder", "height"}:
                raise _unsupported(call)
            return _Control(AnswerField(prompt, "text"), "")
        if kind in {"st.selectbox", "st.multiselect"}:
            if len(call.args) != 2 or keywords - {"key"}:
                raise _unsupported(call)
            options = ast.literal_eval(call.args[1])
            if not isinstance(options, list) or not options or not all(isinstance(item, str) for item in options):
                raise _unsupported(call)
            if kind == "st.selectbox":
                return _Control(AnswerField(prompt, "select", tuple(
                    option for option in options if option != "Select an option"
                )), options[0])
            return _Control(AnswerField(prompt, "multiselect", tuple(options)), [])
        raise _unsupported(call)


@dataclass(frozen=True)
class _Metadata:
    sections: dict
    programs: dict
    fingerprint: str

    def field_variants(self, scope):
        def collect(program):
            for instruction in program:
                if isinstance(instruction, _Branch):
                    yield from collect(instruction.when_true)
                    yield from collect(instruction.when_false)
                elif instruction.field_id is not None:
                    yield instruction.field_id, instruction.value.field

        fields = {}
        for field_id, field in collect(self.programs[scope]):
            variants = fields.setdefault(field_id, [])
            if field not in variants:
                variants.append(field)
        return fields

    def field_ids(self, scope):
        return tuple(self.field_variants(scope))

    def project(self, scope, confirmed):
        values, fields, local = {}, {}, {}

        def run(program):
            for instruction in program:
                if isinstance(instruction, _Branch):
                    run(instruction.when_true if instruction.condition(values) else instruction.when_false)
                    continue
                target, field_id, rule = instruction.path, instruction.field_id, instruction.value
                if field_id is None:
                    _write(target, rule(values), values)
                else:
                    visible = rule.visible is None or rule.visible(values)
                    if visible:
                        fields[field_id] = rule.field
                    answer = deepcopy(confirmed.get(field_id, rule.default)) if visible else None
                    _write(target, answer, values)
                    if len(target) == 1 and field_id in confirmed and visible:
                        local[field_id] = answer

        run(self.programs[scope])
        if scope == "gmlp":
            native = {key: value for key, value in values["profile"].items() if key not in self.sections.values()}
        else:
            native = values[scope]
        return {**native, **local}, fields


def _reviewed_source(source_path, manifest_path):
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        source = source_path.read_bytes()
        if manifest["schema"] != "chat-buddy-d24-owner-contract" or manifest["version"] != 1:
            raise D24CompatibilityError("Unsupported manifest schema or version.")
        if sha256(source).hexdigest() != manifest["source_sha256"]:
            raise D24CompatibilityError("The owner questionnaire source fingerprint changed.")
        return source, manifest
    except D24CompatibilityError:
        raise
    except OSError:
        raise D24CompatibilityError("The owner questionnaire source or manifest could not be read.") from None
    except (SyntaxError, ValueError, TypeError, KeyError, AttributeError, IndexError):
        raise D24CompatibilityError("The owner questionnaire source or manifest could not be interpreted.") from None


def check_metadata_compatibility(fingerprint):
    _, manifest = _reviewed_source(SOURCE, MANIFEST)
    if manifest["source_sha256"] != fingerprint:
        raise D24CompatibilityError(
            "The reviewed questionnaire changed during this session. Editing is disabled to preserve confirmed answers."
        )


def load_metadata(source_path=SOURCE, manifest_path=MANIFEST):
    source, manifest = _reviewed_source(source_path, manifest_path)
    try:
        return _Compiler(ast.parse(source), manifest).compile(manifest["source_sha256"])
    except D24CompatibilityError:
        raise
    except (SyntaxError, ValueError, TypeError, KeyError, AttributeError, IndexError):
        raise D24CompatibilityError("The owner questionnaire source or manifest could not be interpreted.") from None
