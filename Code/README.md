# Forma System Icon Set — downloader

A standalone, static (HTML/CSS/JS, no build step, no framework) icon browser
for the Forma System Icon Set, built to match the Figma file at
`Forma-System-Icon-Set`. Meant to be embedded on
prathmeshwadekar.com/forma-system-icons.

## Running locally

Browsers block `fetch()` on `file://` pages, and the app fetches each icon's
SVG at render time, so you need a static server — you can't just double-click
`index.html`.

```bash
python3 -m http.server 4173
# then open http://localhost:4173
```

Any static file server works (`npx serve`, etc). For deployment, upload the
whole folder as-is to any static host, or embed via `<iframe src="...">` on
the portfolio site.

## Project structure

```
index.html          markup for header, filter sidebar, grid, popups
css/styles.css       all styling — design tokens in :root, dark-mode block at the bottom
js/data.js           icon manifest (CATEGORIES, WEIGHTS, ICONS) — see below
js/app.js            all interactivity: filters, search, grid, popups, export
assets/              UI chrome icons (logo, search, close, copy, share, download, dropper)
icons/<category>/<weight>/<icon-slug>.svg   the actual icon artwork
scripts/build_manifest.py   regenerates js/data.js's ICONS block from the icons/ folder
```

## Current status

**767 unique icons** (3,067 icon+weight SVG files) across **18 categories** ×
**4 weights** (Light/Medium/Bold/Filled), pulled directly from the Figma file
via the design MCP, one call per category. See "Known gaps" below for the
small number of icons that didn't make it and why.

Not yet included: **Social Media** (70+ brand logo icons). That category
uses a different variant scheme in Figma — 2 colour variants (Colour/BW)
per icon instead of 4 weights — so it doesn't fit the current weight-based
filter model. It would need its own UI treatment (a colour toggle instead
of/alongside the weight slider) rather than just a data import.

## How icon recoloring works

Every icon SVG is normalized to `viewBox="0 0 24 24"`. Most icons are
filled shapes using `fill="var(--fill-0, #424242)"`; a smaller set (mostly
in Arrows) are stroked lines using `stroke="var(--stroke-0, #424242)"` with
`fill="none"` on the wrapper. The app sets both `--fill-0` and `--stroke-0`
as CSS custom properties on `<html>` whenever the active colour changes —
every inlined icon on the page (grid tiles + popup preview) picks up
whichever one it uses automatically via CSS inheritance. No per-icon JS
work needed. Downloads (SVG/PNG) resolve `var(--fill-0|stroke-0, ...)` to
the literal hex color before export, so the downloaded file has the color
baked in rather than relying on CSS.

## Adding more icons (e.g. Social Media)

1. **In Figma, select the icon COMPONENT frame — not the inner vector/path.**
   Each icon component is a 24×24 frame; exporting that frame directly gives
   you a correctly-sized, correctly-positioned SVG with no extra work.
2. Select all icon components for a category/weight and use **Export → SVG**
   (native Figma bulk export), or pull via the Figma design MCP's
   `get_design_context` tool on the category's top-level frame — a single
   call returns every icon in that category across all 4 weights at once
   (that's how the existing 18 categories were pulled). `scripts/parse_jsx.py`
   and `scripts/extract_pipeline.py` contain that extraction logic
   (`process_category(category_slug, raw_jsx_text, expected_slugs)`): feed it
   the raw JSX text a `get_design_context` call returns for a category frame
   plus the list of expected icon slugs, and it downloads, normalizes, and
   writes the SVGs into `icons/` for you.
3. Files go into:
   ```
   icons/<category-slug>/<weight>/<icon-slug>.svg
   ```
   Category slugs must match `js/data.js`'s `CATEGORIES` list. Weight must be
   one of `light`, `medium`, `bold`, `filled`. Icon slug = kebab-case
   filename, no extension.
4. Each SVG needs `fill="var(--fill-0, #424242)"` (or `stroke="var(--stroke-0,
   ...)"` + `fill="none"` for line icons) on its path(s), so the app's
   recoloring works.
5. Run the manifest generator:
   ```bash
   python3 scripts/build_manifest.py
   ```
   This scans `icons/` and rewrites `js/data.js`'s `ICONS` object for you —
   no manual JS editing. It also prints a warning for any SVG missing a
   `0 0 24 24` viewBox or a recolorable fill/stroke, so you catch
   normalization issues before they show up as broken icons in the browser.
6. Refresh the page — new categories/weights appear automatically.

## Known gaps / intentional scope

- **~10 icons missing a weight variant or two** out of 767 (roughly 1%) —
  a handful of source-file inconsistencies that weren't worth building
  generic handling for: one icon (`radio-filled` in General) uses a
  completely different variant scheme (`Iconography`/`Weight5` instead of
  `Light`/`Medium`/`Bold`/`Filled`) and is a compound 2-shape icon the
  single-path extraction model doesn't support; a couple of icons have
  duplicate rows in the source Figma page that collapse to one; one icon
  (`file-minus-02`, medium/bold) had an empty asset export from Figma.
- **Multicolour swatch**: opens the RGB/HSL/Hex picker popup (matches the
  Figma spec — "Colours ... multicolour, where a colour selector popup
  opens"), it does not apply a literal rainbow fill to icons.
- **No "All categories" view**: the Figma design uses a single-select
  category radio list with no "all" option, so the app matches that —
  browsing is always scoped to one category (search still spans all
  categories/icons regardless of the selected radio).
- **Social Media category**: not populated — see "Current status" above.
