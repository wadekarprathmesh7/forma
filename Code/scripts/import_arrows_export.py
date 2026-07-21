#!/usr/bin/env python3
"""One-off importer: takes the native Figma bulk-export SVGs dropped in
"Icons export/Arrows" (named "Weight=<Weight>-<slug>.svg" or
"Weight=<Weight><slug>.svg") and writes them into icons/arrows/<weight>/<slug>.svg,
converting the hardcoded fill/stroke colour to the var(--fill-0/--stroke-0, ...)
pattern the app uses for recoloring.
"""
import os
import re

SRC = "/Users/prathmeshwadekar/Documents/Work/Figma/Forma Icon Set/Icons export/Arrows"
DEST = "/Users/prathmeshwadekar/Documents/Work/Figma/Forma Icon Set/forma/Code/icons/arrows"

WEIGHTS = ["Light", "Medium", "Bold", "Filled"]
NAME_RE = re.compile(r"^Weight=(Light|Medium|Bold|Filled)-?(.+)\.svg$")


def recolor(svg_text):
    # Only touch fill/stroke attributes with a literal hex value (not fill="none").
    svg_text = re.sub(
        r'fill="(#[0-9a-fA-F]{3,6})"',
        r'fill="var(--fill-0, \1)"',
        svg_text,
    )
    svg_text = re.sub(
        r'stroke="(#[0-9a-fA-F]{3,6})"',
        r'stroke="var(--stroke-0, \1)"',
        svg_text,
    )
    return svg_text


def main():
    written = []
    skipped = []
    for fname in sorted(os.listdir(SRC)):
        if not fname.endswith(".svg"):
            continue
        m = NAME_RE.match(fname)
        if not m:
            skipped.append(fname)
            continue
        weight, slug = m.group(1).lower(), m.group(2)
        with open(os.path.join(SRC, fname), encoding="utf-8") as f:
            content = f.read()
        content = recolor(content)

        out_dir = os.path.join(DEST, weight)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"{slug}.svg")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        written.append(out_path)

    print(f"Wrote {len(written)} files")
    if skipped:
        print(f"Skipped (unrecognized name): {skipped}")


if __name__ == "__main__":
    main()
