import os
import re
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_jsx import parse_category  # noqa: E402

PROJECT_ICONS = "/Users/prathmeshwadekar/Documents/Work/Figma/Forma Icon Set/Code/icons"
_cache_lock = threading.Lock()


def _px_or_pct_side(inset_str, side, base):
    """Match `<side>-[N%]`, `<side>-N/M`, `<side>-[Npx]`, or bare `<side>-px`
    (Tailwind's literal-1px utility). Returns a percentage of `base`, or None."""
    m = re.search(rf"\b{side}-(?:\[([\d.]+)%\]|(\d+)/(\d+)|\[([\d.]+)px\]|(px)\b)", inset_str)
    if not m:
        return None
    pct, num, den, px, bare_px = m.groups()
    if pct:
        return float(pct)
    if num:
        return float(num) / float(den) * 100
    if px:
        return float(px) / base * 100
    if bare_px:
        return 1 / base * 100
    return None


def _resolve_fixed_size_axis(inset_str, size_prefix, start, end, base):
    """Resolve one axis (horizontal: w/left/right, vertical: h/top/bottom)
    when Tailwind expresses it as a fixed pixel size plus a start-edge
    anchor, rather than two independent percentages. The anchor may be an
    explicit `<start>-[Npx]`/`<start>-[N%]`, a `calc(50%+-Npx)` offset from
    center, or `<start>-1/2 ...-translate-<axis>-1/2` (true centering).
    Returns (start_pct, end_pct) or None if this axis isn't fixed-size.
    """
    size_m = re.search(rf"\b{size_prefix}-(?:\[([\d.]+)px\]|px\b)", inset_str)
    if not size_m:
        return None
    size_px = float(size_m.group(1)) if size_m.group(1) else 1.0

    translate_axis = "x" if start == "left" else "y"
    calc_m = re.search(rf"{start}-\[calc\(50%([+-])([\d.]+)px\)\]", inset_str)
    if calc_m and f"translate-{translate_axis}-1/2" in inset_str:
        sign, offset = calc_m.groups()
        center_px = base / 2 + (float(offset) if sign == "+" else -float(offset))
        start_px = center_px - size_px / 2
    elif f"{start}-1/2" in inset_str and f"translate-{translate_axis}-1/2" in inset_str:
        start_px = (base - size_px) / 2
    else:
        start_pct = _px_or_pct_side(inset_str, start, base)
        if start_pct is None:
            raise ValueError(f"fixed-size inset missing {start} anchor: {inset_str!r}")
        start_px = start_pct / 100 * base
    end_px = base - start_px - size_px
    return start_px / base * 100, end_px / base * 100


def parse_css_inset(inset_str, base=24):
    """CSS inset shorthand -> (top, right, bottom, left) as floats (percent numbers, no %)."""
    inset_str = inset_str.strip()

    horizontal = _resolve_fixed_size_axis(inset_str, "w", "left", "right", base)
    vertical = _resolve_fixed_size_axis(inset_str, "h", "top", "bottom", base)
    if horizontal or vertical:
        left, right = horizontal or (
            _px_or_pct_side(inset_str, "left", base),
            _px_or_pct_side(inset_str, "right", base),
        )
        top, bottom = vertical or (
            _px_or_pct_side(inset_str, "top", base),
            _px_or_pct_side(inset_str, "bottom", base),
        )
        if None in (top, right, bottom, left):
            raise ValueError(f"fixed-size inset missing a side: {inset_str!r}")
        return top, right, bottom, left

    # Tailwind sometimes emits individual top-/right-/bottom-/left- utilities
    # instead of the inset-[...] shorthand (e.g. when a side is a "nice"
    # fraction like 1/4 that has its own utility class).
    side_matches = dict(
        (side, float(pct) if pct else float(num) / float(den) * 100)
        for side, pct, num, den in re.findall(
            r"(top|right|bottom|left)-(?:\[([\d.]+)%\]|(\d+)/(\d+))", inset_str
        )
    )
    if side_matches:
        missing = {"top", "right", "bottom", "left"} - side_matches.keys()
        if missing:
            raise ValueError(f"incomplete per-side inset {inset_str!r}, missing {missing}")
        return side_matches["top"], side_matches["right"], side_matches["bottom"], side_matches["left"]

    parts = [float(p.replace("%", "")) for p in inset_str.split("_") if p]
    if len(parts) == 1:
        return parts[0], parts[0], parts[0], parts[0]
    if len(parts) == 2:
        return parts[0], parts[1], parts[0], parts[1]
    if len(parts) == 4:
        return parts[0], parts[1], parts[2], parts[3]
    raise ValueError(f"unexpected inset shorthand: {inset_str!r}")


def fetch_svg_body(url, cache, retries=6, backoff=3.0):
    with _cache_lock:
        if url in cache:
            return cache[url]

    req = urllib.request.Request(url, headers={"User-Agent": "curl/8.4.0"})
    text = ""
    for attempt in range(retries):
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode("utf-8")
        if text:
            break
        time.sleep(backoff * (attempt + 1))  # 202 Accepted (still rendering / rate-limited): back off and retry
    if not text:
        raise RuntimeError(f"asset never became ready after {retries} retries: {url}")

    m = re.search(r"<svg[^>]*>(.*)</svg>", text, re.S)
    body = m.group(1).strip()
    vb = re.search(r'viewBox="([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)"', text)
    w, h = float(vb.group(3)), float(vb.group(4))
    with _cache_lock:
        cache[url] = (body, w, h)
    return body, w, h


def wrap_24(body, srcw, srch, top, right, bottom, left, base=24):
    offx = left / 100 * base
    offy = top / 100 * base
    w = base * (1 - left / 100 - right / 100)
    h = base * (1 - top / 100 - bottom / 100)
    return (
        f'<svg viewBox="0 0 {base} {base}" fill="none" xmlns="http://www.w3.org/2000/svg">\n'
        f'  <svg x="{offx:.4f}" y="{offy:.4f}" width="{w:.4f}" height="{h:.4f}" '
        f'viewBox="0 0 {srcw:g} {srch:g}" fill="none">\n'
        f"    {body}\n"
        f"  </svg>\n"
        f"</svg>\n"
    )


def _process_one(category_slug, slug, weight, info, cache, dry_run):
    url = info["url"]
    inset = info["inset"]
    if not url or not inset:
        return False, f"{category_slug}/{weight}/{slug}: missing url or inset (url={url!r}, inset={inset!r})"
    try:
        top, right, bottom, left = parse_css_inset(inset)
        body, w, h = fetch_svg_body(url, cache)
        out = wrap_24(body, w, h, top, right, bottom, left)
    except Exception as e:  # noqa: BLE001
        return False, f"{category_slug}/{weight}/{slug}: {e}"

    if not dry_run:
        out_dir = os.path.join(PROJECT_ICONS, category_slug, weight)
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, f"{slug}.svg"), "w") as f:
            f.write(out)
    return True, None


def process_category(category_slug, raw_jsx_text, expected_slugs, cache=None, dry_run=False, max_workers=4):
    if cache is None:
        cache = {}
    results, missing = parse_category(raw_jsx_text, expected_slugs)

    jobs = [
        (slug, weight, info)
        for slug, weights in results.items()
        for weight, info in weights.items()
    ]

    written = 0
    errors = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_process_one, category_slug, slug, weight, info, cache, dry_run): (slug, weight)
            for slug, weight, info in jobs
        }
        for fut in as_completed(futures):
            ok, err = fut.result()
            if ok:
                written += 1
            else:
                errors.append(err)

    return {
        "category": category_slug,
        "expected": len(expected_slugs),
        "parsed": len(results),
        "missing_from_parse": missing,
        "svgs_written": written,
        "errors": errors,
    }
