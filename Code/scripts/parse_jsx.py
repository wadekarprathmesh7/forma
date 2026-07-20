"""
Parses a get_design_context JSX dump for one category frame into:
    { icon_slug: { weight: {url, inset} } }

Works generically off the ternary chains Figma's codegen emits, rather than
hardcoding branch order, so it tolerates icons where some weights share a
value (e.g. Light/Filled sharing the same inset).
"""
import re


def to_pascal(slug):
    pascal = "".join(seg[:1].upper() + seg[1:] for seg in slug.split("-"))
    # Figma's codegen uppercases letters immediately following a digit too
    # (e.g. "3d-rotation" -> "3DRotation"), and prefixes "Component" when
    # the result would otherwise start with a digit (invalid JS identifier).
    pascal = re.sub(r"(?<=\d)([a-z])", lambda m: m.group(1).upper(), pascal)
    return pascal


def pascal_candidates(slug):
    base = to_pascal(slug)
    if base[:1].isdigit():
        return [base, "Component" + base]
    return [base]


def parse_ternary_chain(expr):
    """'A ? "X" : B ? "Y" : "Z"' -> ([(A,"X"), (B,"Y")], "Z")"""
    parts = []
    remaining = expr.strip()
    while "?" in remaining:
        cond, rest = remaining.split("?", 1)
        val, remaining = rest.split(":", 1)
        parts.append((cond.strip(), val.strip()))
    return parts, remaining.strip()


def extract_bool_vars(body):
    """Find `const isX = <js bool expr>;` declarations in a function body."""
    return dict(re.findall(r"const (is\w+) = ([^;]+);", body))


def eval_condition(cond, weight, bool_vars, _resolving=None):
    cond = cond.strip()
    if _resolving is None:
        _resolving = set()

    if cond == f'weight === "Light"' or cond == "isLight":
        return weight == "Light"
    m = re.fullmatch(r'weight === "(\w+)"', cond)
    if m:
        return weight == m.group(1)
    if ".includes(weight)" in cond:
        vals = re.findall(r'"([^"]+)"', cond)
        return weight in vals
    if cond in bool_vars:
        if cond in _resolving:
            raise ValueError(f"circular reference resolving {cond!r}")
        return eval_js_bool(bool_vars[cond], weight, bool_vars, _resolving | {cond})
    raise ValueError(f"unrecognized condition: {cond!r}")


def eval_js_bool(expr, weight, bool_vars, _resolving=None):
    """Evaluate a JS boolean expression (||, &&, comparisons, var refs)."""
    expr = expr.strip()
    if "||" in expr:
        return any(eval_js_bool(p, weight, bool_vars, _resolving) for p in expr.split("||"))
    if "&&" in expr:
        return all(eval_js_bool(p, weight, bool_vars, _resolving) for p in expr.split("&&"))
    return eval_condition(expr, weight, bool_vars, _resolving)


def resolve(expr, weight, strip_quotes, bool_vars):
    parts, default = parse_ternary_chain(expr)
    val = default
    for cond, candidate in parts:
        if eval_js_bool(cond, weight, bool_vars):
            val = candidate
            break
    return val.strip('"') if strip_quotes else val


def resolve_inset_expr(raw, weight, bool_vars):
    """Resolve a className expression (static string, template literal with
    one or more ${...} interpolations, or a mix of both) down to a flat
    utility-class string for one weight, e.g.
    '`absolute bottom-1/4 left-1/4 top-1/4 ${isBoldOrFilled ? "right-[20.83%]" : ...}`'
    -> 'absolute bottom-1/4 left-1/4 top-1/4 right-[20.83%]'
    """
    raw = raw.strip()
    if raw[:1] in "`\"" and raw[-1:] == raw[:1]:
        raw = raw[1:-1]

    def repl(m):
        return resolve(m.group(1), weight, strip_quotes=True, bool_vars=bool_vars)

    resolved = re.sub(r"\$\{(.+?)\}", repl, raw)
    resolved = resolved.replace("absolute ", "", 1).strip()
    if resolved.startswith("inset-[") and resolved.endswith("]"):
        resolved = resolved[len("inset-["):-1]
    return resolved


WEIGHTS = ["Light", "Medium", "Bold", "Filled"]


def parse_category(raw_text, expected_slugs):
    """expected_slugs: list of ground-truth icon slugs for this category (from metadata)."""
    url_map = dict(re.findall(r'const (img\w*) = "(https://[^"]+)";', raw_text))

    func_blocks = {}
    for m in re.finditer(
        r"\nfunction (\w+)\([^)]*\)[^{]*\{(.*?)\n\}(?=\n)",
        raw_text,
        re.S,
    ):
        func_blocks[m.group(1)] = m.group(2)

    results = {}
    missing = []
    for slug in expected_slugs:
        if slug == "icon_placeholder":
            continue  # unrenamed template row, not a real icon
        body = None
        for pascal in pascal_candidates(slug):
            body = func_blocks.get(pascal)
            if body is not None:
                break
        if body is None:
            missing.append(slug)
            continue

        src_m = re.search(r"<img\b[^>]*\bsrc=\{([^}]+)\}", body)
        # Non-greedy but forbidden from crossing into a nested <div>, so this
        # can't accidentally span from the OUTER wrapper div (which also
        # starts with `<div className=`) through to the inner one. className
        # is either braced (`={...}`, dynamic) or a plain string (`="..."`,
        # emitted when the value is the same across all weights).
        inset_holder_m = re.search(
            r'<div className=(?:\{((?:(?!<div).)*?)\}|("[^"]*"))(?:\s+id=\{[^}]*\})?\s+data-name="Union"',
            body, re.S,
        )

        if src_m is None:
            missing.append(slug)
            continue

        bool_vars = extract_bool_vars(body)
        per_weight = {}
        for weight in WEIGHTS:
            var_name = resolve(src_m.group(1), weight, strip_quotes=False, bool_vars=bool_vars)
            url = url_map.get(var_name)
            inset = None
            if inset_holder_m:
                raw_inset = inset_holder_m.group(1) if inset_holder_m.group(1) is not None else inset_holder_m.group(2)
                inset = resolve_inset_expr(raw_inset, weight, bool_vars)
            per_weight[weight.lower()] = {"url": url, "inset": inset}
        results[slug] = per_weight

    return results, missing
