#!/usr/bin/env python3
"""
Regenerates the ICONS block in js/data.js by scanning icons/<category>/<weight>/*.svg.

Run this after dropping newly exported SVGs into the icons/ folder:
    python3 scripts/build_manifest.py

It only rewrites the auto-generated ICONS object — CATEGORIES, WEIGHTS and
everything else in js/data.js is left untouched. It also prints warnings for
any SVG that isn't normalized to a 24x24 viewBox with a var(--fill-0, ...)
fill, since those icons won't recolor correctly in the app.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICONS_DIR = os.path.join(ROOT, "icons")
DATA_JS = os.path.join(ROOT, "js", "data.js")

WEIGHTS = ["light", "medium", "bold", "filled"]

START_MARKER = "// icons[category-slug] = { [weight]: [iconSlug, ...] }\nconst ICONS = "
END_MARKER = ";"


def scan():
    icons = {}
    warnings = []
    if not os.path.isdir(ICONS_DIR):
        return icons, warnings

    for category_slug in sorted(os.listdir(ICONS_DIR)):
        category_path = os.path.join(ICONS_DIR, category_slug)
        if not os.path.isdir(category_path) or category_slug.startswith("."):
            continue
        by_weight = {}
        for weight in WEIGHTS:
            weight_path = os.path.join(category_path, weight)
            if not os.path.isdir(weight_path):
                continue
            slugs = []
            for fname in sorted(os.listdir(weight_path)):
                if not fname.endswith(".svg"):
                    continue
                slug = fname[:-4]
                slugs.append(slug)
                warnings.extend(validate_svg(os.path.join(weight_path, fname), category_slug, weight, slug))
            if slugs:
                by_weight[weight] = slugs
        if by_weight:
            icons[category_slug] = by_weight
    return icons, warnings


def validate_svg(path, category, weight, slug):
    warnings = []
    with open(path, encoding="utf-8") as f:
        content = f.read()
    label = f"icons/{category}/{weight}/{slug}.svg"
    if 'viewBox="0 0 24 24"' not in content:
        warnings.append(f"  {label}: outer viewBox is not \"0 0 24 24\" (icon may render off-grid)")
    if "var(--fill-0" not in content and "var(--stroke-0" not in content:
        warnings.append(f"  {label}: no var(--fill-0, ...) or var(--stroke-0, ...) found (icon won't recolor)")
    return warnings


def render_js(icons):
    lines = ["const ICONS = {"]
    for category_slug, by_weight in icons.items():
        lines.append(f'  "{category_slug}": {{')
        for weight in WEIGHTS:
            if weight not in by_weight:
                continue
            slugs_json = json.dumps(by_weight[weight])
            lines.append(f"    {weight}: {slugs_json},")
        lines.append("  },")
    lines.append("};")
    return "\n".join(lines)


def main():
    icons, warnings = scan()
    total = sum(len(slugs) for by_weight in icons.values() for slugs in by_weight.values())

    with open(DATA_JS, encoding="utf-8") as f:
        data_js = f.read()

    start_idx = data_js.find(START_MARKER)
    if start_idx == -1:
        print("Could not find ICONS block marker in js/data.js — aborting.", file=sys.stderr)
        sys.exit(1)
    body_start = start_idx + len(START_MARKER)
    end_idx = data_js.find("\n};", body_start)
    if end_idx == -1:
        print("Could not find end of ICONS block in js/data.js — aborting.", file=sys.stderr)
        sys.exit(1)

    new_block = render_js(icons).replace("const ICONS = ", "", 1).strip()

    new_data_js = data_js[:body_start] + new_block + data_js[end_idx + len("\n};"):]
    with open(DATA_JS, "w", encoding="utf-8") as f:
        f.write(new_data_js)

    print(f"Wrote {total} icon entries across {len(icons)} categories to js/data.js")
    if warnings:
        print(f"\n{len(warnings)} warning(s):")
        for w in warnings:
            print(w)


if __name__ == "__main__":
    main()
