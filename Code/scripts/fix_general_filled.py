#!/usr/bin/env python3
"""Fix the ~50 'Filled' weight icons in the General category that were
placeholder-duplicated from Light during the original bulk extraction.

Each icon here uses a much simpler codegen pattern than Arrows: a single
outer absolute box (percent inset of 24x24), sometimes with ONE extra
nested div holding a small bleed inset (mixed px/percent) before the <img>,
and never any rotation. This script stretch-fits each raw Figma asset into
(box [+ bleed]) and writes the flattened 24x24 SVG, recoloring stroke/fill
to the var(--stroke-0/--fill-0) tokens the app uses.
"""
import math
import os
import re
import urllib.request

DEST = "/Users/prathmeshwadekar/Documents/Work/Figma/Forma Icon Set/forma/Code/icons/general/filled"
CACHE_DIR = "/private/tmp/claude-501/-Users-prathmeshwadekar-Documents-Work-Figma-Forma-Icon-Set/eb9062fb-485c-4b3b-bb44-0c6cddb886be/scratchpad/general_fix/raw"
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(DEST, exist_ok=True)


def frac_or_pct(tok):
    """'14.58%' -> 14.58 | '1/4' -> 25.0 | '1/2' -> 50.0"""
    tok = tok.strip()
    if tok.endswith("%"):
        return float(tok[:-1])
    if "/" in tok:
        n, d = tok.split("/")
        return float(n) / float(d) * 100
    raise ValueError(f"unrecognized token: {tok!r}")


def parse_box(expr):
    """Outer box class string -> (top, right, bottom, left) as % of 24."""
    expr = expr.strip()
    # individual utilities: "bottom-1/2 left-1/4 right-1/4 top-1/2"
    sides = dict(re.findall(r"\b(top|right|bottom|left)-(\[[\d.]+%\]|\d+/\d+)", expr))
    if sides:
        def g(s):
            return frac_or_pct(sides[s].strip("[]"))
        return g("top"), g("right"), g("bottom"), g("left")
    # bracket shorthand: inset-[T%_R%_B%_L%] / inset-[V%_H%] / inset-[U%]
    m = re.search(r"inset-\[([^\]]+)\]", expr)
    if m:
        parts = [frac_or_pct(p) for p in m.group(1).split("_") if p]
        if len(parts) == 1:
            return parts[0], parts[0], parts[0], parts[0]
        if len(parts) == 2:
            return parts[0], parts[1], parts[0], parts[1]
        if len(parts) == 4:
            return parts[0], parts[1], parts[2], parts[3]
        raise ValueError(f"bad inset shorthand: {expr!r}")
    # plain fraction shorthand: inset-1/4
    m = re.search(r"inset-(\d+/\d+)\b", expr)
    if m:
        v = frac_or_pct(m.group(1))
        return v, v, v, v
    raise ValueError(f"unrecognized box expr: {expr!r}")


def parse_bleed(expr, box_w, box_h):
    """Bleed class string (may mix px & %, signed, 1/2/4-value shorthand)
    -> (top, right, bottom, left) as SIGNED pixels, same convention as CSS
    inset: positive shrinks the box inward on that side, negative expands
    it outward."""
    if expr is None:
        return 0.0, 0.0, 0.0, 0.0
    m = re.search(r"inset-\[([^\]]+)\]", expr)
    tokens = m.group(1).split("_") if m else expr.split("_")

    def resolve(tok, dim):
        tok = tok.strip()
        sign = -1.0 if tok.startswith("-") else 1.0
        tok = tok.lstrip("-")
        if tok.endswith("px"):
            val = float(tok[:-2])
        else:
            val = float(tok.rstrip("%")) / 100 * dim
        return sign * val

    if len(tokens) == 1:
        v, vh = resolve(tokens[0], box_h), resolve(tokens[0], box_w)
        return v, vh, v, vh
    if len(tokens) == 2:
        vert, horiz = resolve(tokens[0], box_h), resolve(tokens[1], box_w)
        return vert, horiz, vert, horiz
    if len(tokens) == 4:
        return (
            resolve(tokens[0], box_h),
            resolve(tokens[1], box_w),
            resolve(tokens[2], box_h),
            resolve(tokens[3], box_w),
        )
    raise ValueError(f"bad bleed shorthand: {expr!r}")


def fetch(asset_id):
    path = os.path.join(CACHE_DIR, f"{asset_id}.svg")
    if not os.path.exists(path):
        url = f"https://www.figma.com/api/mcp/asset/{asset_id}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        with open(path, "wb") as f:
            f.write(data)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = re.search(r"<svg[^>]*>(.*)</svg>", text, re.S)
    body = m.group(1).strip()
    vb = re.search(r'viewBox="([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)"', text)
    w, h = float(vb.group(3)), float(vb.group(4))
    return body, w, h


def recolor(svg_text):
    svg_text = re.sub(r'stroke="(#[0-9a-fA-F]{3,6})"', r'stroke="var(--stroke-0, \1)"', svg_text)
    svg_text = re.sub(r'fill="(#[0-9a-fA-F]{3,6})"', r'fill="var(--fill-0, \1)"', svg_text)
    return svg_text


# slug: (outer_box_expr, bleed_expr_or_None, asset_id)
ICONS = {
    "check-tik-circle": ("inset-[14.58%]", None, "8041cd3c-cfa6-4394-b6d7-efed77fe8a08"),
    "check-tik-square": ("inset-[14.58%]", None, "1bf6d74a-1bcd-464c-a79e-4feb02a55206"),
    "close-cancel": ("inset-[29.17%]", "inset-[-10%]", "aa01f2b9-deed-466a-a2dc-33a2a7880c03"),
    "close-cancel-circle": ("inset-[16.67%]", None, "8a551aa6-2227-42b1-867e-5b0f56c2c482"),
    "close-cancel-square": ("inset-[14.58%]", None, "94457e2d-d249-4b6c-b684-c7323d6bbb78"),
    "minus": ("bottom-1/2 left-1/4 right-1/4 top-1/2", "inset-[-1px_-8.33%]", "32e5e300-20fa-4ca1-9f80-85dfef118be9"),
    "minus-circle": ("inset-[14.58%]", None, "4ef91055-641e-4581-8def-938c597301d2"),
    "minus-square": ("inset-[14.58%]", None, "bc6652e5-9cdd-44be-9c0c-97f446919b44"),
    "plus": ("inset-1/4", "inset-[-8.33%]", "59d83f8b-c49f-41b0-acaf-42177eb8b165"),
    "plus-circle": ("inset-[14.58%]", None, "c247ab2b-0649-4a07-a276-ceb5fc04445b"),
    "plus-square": ("inset-[14.58%]", None, "06d4e952-7f95-441b-beaa-0b854c9fd05f"),
    "delete": ("bottom-[16.67%] left-1/4 right-1/4 top-[16.67%]", "inset-[-6.25%_-8.33%_-3.13%_-8.33%]", "1d6e19b3-3105-4c54-8d3e-4e2976673ef1"),
    "search": ("inset-1/4", "inset-[-8.33%]", "fef12a57-ea5f-4744-bc16-7ca56b752a3d"),
    "filter-01": ("bottom-[29.17%] left-1/4 right-1/4 top-[29.17%]", "inset-[-10%_-8.33%]", "eb46fcba-bfb8-44ee-9d02-2675969f8e85"),
    "filter-02": ("inset-[16.67%]", "inset-[-3.13%_4.13%_4.61%_4.13%]", "8ead5770-4bd7-4029-9ecc-de17bf615f1f"),
    "heart": ("inset-[20.83%_16.67%_19.17%_16.67%]", "inset-[-3.47%_-3.12%_-3.47%_-3.11%]", "350a2bee-23d8-400a-88c6-ec1f8ae5cabb"),
    "hearts": ("inset-[15.88%_5.8%_13.55%_9.27%]", None, "204fee5c-89bb-43c0-a94b-8844fc56ba2f"),
    "download": ("inset-1/4", "inset-[-8.33%]", "37b195c1-a3c2-4653-962f-465edeb13829", -90),
    "link-01": ("inset-[33.33%_16.67%]", "inset-[-12.5%_-6.25%]", "b538e936-a863-4f68-8cfd-dfdcb8f87db9"),
    "link-02": ("inset-[14.64%]", "inset-[-12.5%_-6.25%]", "9ddc5d3f-2a39-4364-80bb-f1c41f5db4cf", -45, ((33.3333, 33.3333), (66.6667, 66.6667))),
    "link-broken-01": ("inset-[12.5%_16.67%]", "inset-[-5.56%_-6.25%]", "2139260c-077e-4ca4-a24a-866bf8b02ede"),
    "link-broken-02": ("inset-[-1.31%_-1.31%_-1.31%_-1.3%]", "inset-[-5.31%_-6.25%]", "d910c75a-8a75-4b70-9ab9-90e9b624078e", -45, ((54.0603, 54.0603), (45.9397, 45.9397))),
    "settings-01": ("inset-[14.58%_16.41%]", None, "8289bef1-d5a6-4407-a92c-fc86849ee136"),
    "settings-03": ("inset-[14.58%_18.75%]", None, "87feee6c-bc7a-4fda-98b3-963472163769"),
    "check-verified": ("inset-[14.29%]", None, "53cf1cdb-ed6f-4a9d-b08d-c704b615187b"),
    "cloud-upload": ("inset-[14.58%_14.58%_12.5%_14.58%]", None, "d419a40a-e82d-43f8-ac25-dc392de339f9"),
    "cloud-download": ("inset-[14.58%_14.58%_12.5%_14.58%]", None, "ae230134-624a-44e5-a01c-93d4fd42871c"),
    "divide": ("bottom-1/4 left-[20.83%] right-[20.83%] top-1/4", "inset-[-8.33%_-7.14%]", "6e1ecf28-b912-4ed3-a2bc-78a99fed154e"),
    "checkbox-checked": ("inset-[16.67%]", None, "43b95699-b72b-4014-8646-01abbbc92710"),
    "checkbox-indeterminate": ("inset-[16.67%]", None, "0cc7ee6d-2ade-4472-8ad2-396e29cf89dd"),
    "radio-empty": ("inset-[16.67%]", None, "65dfc689-959d-42c5-b631-03acb622bf73"),
    "eye-closed": ("bottom-1/4 left-[16.17%] right-[16.04%] top-[47.92%]", "inset-[-15.39%_-6.15%_-15.38%_-6.15%]", "6b6edf62-e113-41e3-bdad-1e5a2c908034"),
    "accessibility": ("inset-[12.5%_18.75%_16.67%_18.75%]", "inset-[-5.88%_-6.67%]", "9c888ce0-4775-45a2-867c-7c89d0dc1659"),
    "accessible": ("inset-[16.67%_33.33%_16.67%_29.17%]", "inset-[-6.25%_-11.11%]", "073626e2-1135-4b46-926c-9f07dc07d445"),
    "activity": ("bottom-1/4 left-[12.5%] right-[12.5%] top-1/4", "inset-[-8.33%_-5.56%]", "94fff8dd-1a7a-4502-862f-3444c29537f1"),
    "heart-activity": ("inset-[14.58%_10.42%_14.06%_10.42%]", None, "6dcf8176-097f-4c60-96fe-92d4e72d8572"),
    "home": ("bottom-[20.83%] left-1/4 right-1/4 top-[22.09%]", "inset-[-3.65%_-4.17%]", "8dbc6439-1626-440a-9bc1-b6d3785cd556"),
    "medical": ("inset-[16.67%]", "inset-[-3.13%]", "b1ea45a1-f9b5-4570-803a-5748fc878e15"),
    "medical-square-hospital": ("inset-[10.42%]", None, "1ee2acff-1738-403b-8cbd-2ab258a3eafc"),
    "bookmark": ("bottom-[18.38%] left-1/4 right-1/4 top-[20.83%]", "inset-[-3.43%_-4.17%]", "89d9a6ac-ec57-490b-83d2-80fc559ea1c0"),
    "bookmark-added": ("inset-[18.75%_22.92%_16.3%_22.92%]", None, "2d3dc93c-6665-4773-b8a8-66404e5a252d"),
    "add-bookmark": ("inset-[18.75%_22.92%_16.3%_22.92%]", None, "a614c37f-b55f-4cc5-ab2e-43f2d9aa3449"),
    "remove-bookmark": ("inset-[18.75%_22.92%_16.3%_22.92%]", None, "2c2f3f52-6ff1-4d22-ba09-882cf4b4c08a"),
    "share-03": ("inset-[16.67%_12.5%]", "inset-[-3.13%_-2.78%]", "cb8a4676-f8d2-4628-acf3-6b60dfcd939c"),
    "target-03": ("inset-[12.5%]", None, "6703e696-49de-4ee8-9c2f-55e25dd85754"),
}

# icons whose Filled variant is a plain unfilled stroked rounded-rect
STROKE_RECT_ICONS = {
    "checkbox-empty": ("16.67%", 4, 2),
}


def compose_stroke_rect(inset_pct, rx, stroke_width):
    top, right, bottom, left = parse_box(f"inset-[{inset_pct}]")
    x = left / 100 * 24
    y = top / 100 * 24
    w = 24 - x - (right / 100 * 24)
    h = 24 - y - (bottom / 100 * 24)
    svg = (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">\n'
        f'<rect x="{x:.4f}" y="{y:.4f}" width="{w:.4f}" height="{h:.4f}" rx="{rx}" '
        f'fill="none" stroke="var(--stroke-0, #424242)" stroke-width="{stroke_width}"/>\n</svg>\n'
    )
    return svg

MULTI_ICONS = {
    "settings-02": [
        ("inset-[20.83%_20.83%_62.5%_20.83%]", "inset-[-25%_-7.14%]", "17cb2fdf-ad2d-42e1-b366-3b3fb5ca80ea"),
        ("inset-[62.5%_20.83%_20.83%_20.83%]", "inset-[-25%_-7.14%]", "a06c5ee2-70a1-47ca-8305-2eb48802f929", 0, None, "x"),
    ],
    "eye-open": [
        ("bottom-1/4 left-[17.59%] right-[17.59%] top-1/4", "inset-[-8.33%_-6.42%]", "aef3ad0a-a2db-452f-bcbe-82718c8d5a0f"),
        ("inset-[37.5%]", "inset-[-16.67%]", "32693761-9ea4-416e-bfd6-5005504c9866"),
    ],
}

# icons whose Filled variant is plain rounded rects (no image asset at all)
RECT_ICONS = {
    "dashboard": [
        ("20.83%_58.33%_45.83%_20.83%", 2),
        ("66.67%_58.33%_20.83%_20.83%", 2),
        ("20.83%_20.83%_66.67%_54.17%", 2),
        ("45.83%_20.83%_20.83%_54.17%", 2),
    ],
    "projects-apps": [
        ("20.83%_58.33%_58.33%_20.83%", 1),
        ("58.33%_58.33%_20.83%_20.83%", 1),
        ("20.83%_20.83%_58.33%_58.33%", 1),
        ("58.33%_20.83%_20.83%_58.33%", 1),
    ],
}


def compose_rects(insets):
    rects = []
    for inset_str, rx in insets:
        top, right, bottom, left = parse_box(f"inset-[{inset_str}]")
        x = left / 100 * 24
        y = top / 100 * 24
        w = 24 - x - (right / 100 * 24)
        h = 24 - y - (bottom / 100 * 24)
        rects.append(
            f'<rect x="{x:.4f}" y="{y:.4f}" width="{w:.4f}" height="{h:.4f}" rx="{rx}" '
            f'fill="var(--fill-0, #424242)" stroke="var(--stroke-0, #424242)"/>'
        )
    svg = (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">\n'
        + "\n".join(rects)
        + "\n</svg>\n"
    )
    return svg


def compose_part(outer_expr, bleed_expr, asset_id, rotation=0, hypot=None, flip=None):
    top, right, bottom, left = parse_box(outer_expr)
    box_x = left / 100 * 24
    box_y = top / 100 * 24
    box_w = 24 - box_x - (right / 100 * 24)
    box_h = 24 - box_y - (bottom / 100 * 24)
    cx, cy = box_x + box_w / 2, box_y + box_h / 2

    if hypot:
        (hw_pct, hh_pct), (ww_pct, wh_pct) = hypot
        pre_h = math.hypot(hw_pct / 100 * box_w, hh_pct / 100 * box_h)
        pre_w = math.hypot(ww_pct / 100 * box_w, wh_pct / 100 * box_h)
    else:
        swapped = rotation in (90, -90, 270, -270)
        pre_w, pre_h = (box_h, box_w) if swapped else (box_w, box_h)

    bt, br, bb, bl = parse_bleed(bleed_expr, pre_w, pre_h)
    eff_x = (cx - pre_w / 2) + bl
    eff_y = (cy - pre_h / 2) + bt
    eff_w = pre_w - bl - br
    eff_h = pre_h - bt - bb

    body, srcw, srch = fetch(asset_id)
    inner = (
        f'<svg x="{eff_x:.4f}" y="{eff_y:.4f}" width="{eff_w:.4f}" height="{eff_h:.4f}" '
        f'viewBox="0 0 {srcw:g} {srch:g}" fill="none">{body}</svg>'
    )
    if rotation:
        inner = f'<g transform="rotate({rotation} {cx:.4f} {cy:.4f})">{inner}</g>'
    if flip == "x":
        inner = f'<g transform="translate({2*cx:.4f} 0) scale(-1 1)">{inner}</g>'
    elif flip == "y":
        inner = f'<g transform="translate(0 {2*cy:.4f}) scale(1 -1)">{inner}</g>'
    return inner


def compose(slug, outer_expr, bleed_expr, asset_id, rotation=0, hypot=None):
    inner = compose_part(outer_expr, bleed_expr, asset_id, rotation, hypot)
    svg = (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">\n'
        f"{inner}\n</svg>\n"
    )
    return recolor(svg)


def compose_multi(parts):
    inners = [compose_part(*p) for p in parts]
    svg = (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">\n'
        + "\n".join(inners)
        + "\n</svg>\n"
    )
    return recolor(svg)


def main():
    written = []
    for slug, spec in ICONS.items():
        outer, bleed, asset_id = spec[0], spec[1], spec[2]
        rotation = spec[3] if len(spec) > 3 else 0
        hypot = spec[4] if len(spec) > 4 else None
        svg = compose(slug, outer, bleed, asset_id, rotation, hypot)
        out_path = os.path.join(DEST, f"{slug}.svg")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(svg)
        written.append(out_path)
    for slug, parts in MULTI_ICONS.items():
        svg = compose_multi(parts)
        out_path = os.path.join(DEST, f"{slug}.svg")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(svg)
        written.append(out_path)
    for slug, insets in RECT_ICONS.items():
        svg = compose_rects(insets)
        out_path = os.path.join(DEST, f"{slug}.svg")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(svg)
        written.append(out_path)
    for slug, (inset_pct, rx, sw) in STROKE_RECT_ICONS.items():
        svg = compose_stroke_rect(inset_pct, rx, sw)
        out_path = os.path.join(DEST, f"{slug}.svg")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(svg)
        written.append(out_path)
    print(f"Wrote {len(written)} files")


if __name__ == "__main__":
    main()
