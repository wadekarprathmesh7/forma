#!/usr/bin/env python3
"""Compose the 28 broken Arrows icons from raw Figma crop exports.

Each icon in Figma's codegen is expressed as: an outer absolute box (percent
inset of a 24x24 frame), an inner div with a small NEGATIVE inset (bleed, to
accommodate round stroke-cap overflow) that holds a cropped <img>, and
optionally a rotation wrapper (rotate-180 or ±90 with w/h swapped) for icons
that reuse another icon's asset rotated.

This script stretch-fits each raw cropped asset into (box expanded by bleed),
optionally rotated about the box center, producing a flat 24x24 SVG per
weight, then recolors stroke/fill to the var(--stroke-0/--fill-0) tokens the
app uses for live recoloring.
"""
import os
import re
import urllib.request

DEST = "/Users/prathmeshwadekar/Documents/Work/Figma/Forma Icon Set/forma/Code/icons/arrows"
CACHE_DIR = "/private/tmp/claude-501/-Users-prathmeshwadekar-Documents-Work-Figma-Forma-Icon-Set/eb9062fb-485c-4b3b-bb44-0c6cddb886be/scratchpad/arrows_fix/raw"
os.makedirs(CACHE_DIR, exist_ok=True)

WEIGHT_GROUPS = {"light": "Light", "medium": "Medium", "boldfilled": ("Bold", "Filled")}


def u(v):
    return v if isinstance(v, tuple) else (v, v)


# slug: box(top,right,bottom,left), bleed per group (vert,horiz), asset id per group, rotation deg
ICONS = {
    "chevron-right": dict(
        box=(25, 37.5, 25, 37.5), rotation=180,
        bleed={"light": u(-4.17) if False else (-4.17, -8.33), "medium": (-6.25, -12.5), "boldfilled": (-8.33, -16.67)},
        asset={"light": "96753702-8fb9-40d1-bb49-0d440cd6b180", "medium": "8755f05f-217c-4aa8-b0af-7bc77d60e920", "boldfilled": "18282acd-17bf-4ee2-8454-4ead6cdfdfdb"},
    ),
    "chevron-down": dict(
        box=(37.5, 25, 37.5, 25), rotation=-90,
        bleed={"light": (-4.17, -8.33), "medium": (-6.25, -12.5), "boldfilled": (-8.33, -16.67)},
        asset={"light": "6e18c6de-d3d4-45fe-a70e-ecd8423424c3", "medium": "4980e505-99c8-41d2-8228-e98b0b412f2b", "boldfilled": "9934eefe-bc0b-431d-a0a2-8f9c6896f7ac"},
    ),
    "chevron-left-small": dict(
        box=(33.33, 41.67, 33.33, 41.67), rotation=0,
        bleed={"light": (-6.25, -12.5), "medium": (-9.38, -18.75), "boldfilled": (-12.5, -25)},
        asset={"light": "2fb7d163-471e-4ba4-bccc-94add9565814", "medium": "acd90769-e639-4250-9dcc-d1f99f8ab3dc", "boldfilled": "6bbc4bae-379b-4c1c-a07b-b166707b6e93"},
    ),
    "chevron-up-small": dict(
        box=(41.67, 33.33, 41.67, 33.33), rotation=0,
        bleed={"light": (-12.5, -6.25), "medium": (-18.75, -9.38), "boldfilled": (-25, -12.5)},
        asset={"light": "7658ab08-d3b1-4f9d-a5c4-f18dbe0f4158", "medium": "b18d8af8-aa0c-499a-aa64-dc65a2b24260", "boldfilled": "c2e30b50-9633-4cd9-a7e3-a7158db24fad"},
    ),
    "chevron-right-small": dict(
        box=(33.33, 41.67, 33.33, 41.67), rotation=180,
        bleed={"light": (-6.25, -12.5), "medium": (-9.38, -18.75), "boldfilled": (-12.5, -25)},
        asset={"light": "e1cbb1b9-08b6-4a61-b565-fc84ed441ff0", "medium": "67425567-342d-42c4-9970-e5103f1baa60", "boldfilled": "b0dbaa2f-d127-4d1b-b78d-e91241d4a126"},
    ),
    "chevron-down-small": dict(
        box=(41.67, 33.33, 41.67, 33.33), rotation=0,
        bleed={"light": (-12.5, -6.25), "medium": (-18.75, -9.38), "boldfilled": (-25, -12.5)},
        asset={"light": "1ce7550d-49ad-451d-845f-1576281c2ba7", "medium": "555e1f58-fda5-4057-9e5b-7b489b1d62bf", "boldfilled": "21bf93ff-1a73-49c5-b413-b469814f7b4b"},
    ),
    "arrow-left": dict(
        box=(25, 25, 25, 25), rotation=0,
        bleed={"light": (-4.17, -4.17), "medium": (-6.25, -6.25), "boldfilled": (-8.33, -8.33)},
        asset={"light": "43ff9cf1-aa20-45c6-a4f8-9171ee120d26", "medium": "11c050c6-af84-456d-91e5-4d66d4a168fe", "boldfilled": "49ae6693-99f2-44d0-8cd7-924e91c873bd"},
    ),
    "arrow-up": dict(
        box=(25, 25, 25, 25), rotation=0,
        bleed={"light": (-4.17, -4.17), "medium": (-6.25, -6.25), "boldfilled": (-8.33, -8.33)},
        asset={"light": "fc8c97d1-b212-4614-98be-5cc358ac69cf", "medium": "8db58b4f-a318-4474-85fa-8b0d88d7e0f1", "boldfilled": "dfcb902e-4955-4fa7-8016-55aa20208156"},
    ),
    "arrow-right": dict(
        box=(25, 25, 25, 25), rotation=0,
        bleed={"light": (-4.17, -4.17), "medium": (-6.25, -6.25), "boldfilled": (-8.33, -8.33)},
        asset={"light": "6d6114e6-e825-47d8-bcb3-39a8a237d8f3", "medium": "67df0f40-9a8d-4ba1-8cd9-0249ddf97cfb", "boldfilled": "243da53c-1455-4ae8-99ac-00512bb12e24"},
    ),
    "arrow-down": dict(
        box=(25, 25, 25, 25), rotation=0,
        bleed={"light": (-4.17, -4.17), "medium": (-6.25, -6.25), "boldfilled": (-8.33, -8.33)},
        asset={"light": "f1f20103-bb1d-4b3c-9372-480f8d9cecbb", "medium": "87e6bc8c-09fb-457c-affc-31a02f2c10e7", "boldfilled": "b81382df-6918-49bc-81a1-05c3b84ccda6"},
    ),
    "arrow-down-right": dict(
        box=(32.32, 32.32, 32.32, 32.32), rotation=0,
        bleed={"light": (-5.89, -5.89), "medium": (-8.84, -8.84), "boldfilled": (-11.79, -11.79)},
        asset={"light": "ba03928f-fa6e-43c7-9e0f-2ccca73dbd12", "medium": "b14eb9f4-40b3-4e24-aeb5-6fdfab1b147d", "boldfilled": "be1a6b0d-2cb4-4309-a417-707ddeca5658"},
    ),
    "arrow-down-left": dict(
        box=(32.32, 32.32, 32.32, 32.32), rotation=0,
        bleed={"light": (-5.89, -5.89), "medium": (-8.84, -8.84), "boldfilled": (-11.79, -11.79)},
        asset={"light": "ecb36f78-3cc0-440f-b190-70e70dbc9bfc", "medium": "dafd75a1-3bbf-4e83-8521-ce0040b32254", "boldfilled": "77dab956-fd09-4da2-b458-f83df64ae309"},
    ),
    "unfold-more-horizontal": dict(
        box=(33.33, 20.83, 33.33, 20.83), rotation=0,
        bleed={"light": (-6.25, -3.57), "medium": (-9.38, -5.36), "boldfilled": (-12.5, -7.14)},
        asset={"light": "bc80078e-b412-4a5b-b5c6-e01fce2955cf", "medium": "434b6722-6811-40bf-b174-92352b38bdb4", "boldfilled": "9dd09df6-2db4-4740-8cd3-0c0b9d5935a5"},
    ),
    "unfold-less-horizontal": dict(
        box=(33.33, 20.83, 33.33, 20.83), rotation=0,
        bleed={"light": (-6.25, -3.57), "medium": (-9.38, -5.36), "boldfilled": (-12.5, -7.14)},
        asset={"light": "c43308d5-ba13-45d1-9237-3021d1f20d5b", "medium": "58bb12f6-1d1e-4db5-9ae9-c086d50530b0", "boldfilled": "36319fe8-9886-405e-9160-22b6ff13df2b"},
    ),
    "unfold-more-vertical": dict(
        box=(20.83, 33.33, 20.83, 33.33), rotation=0,
        bleed={"light": (-3.57, -6.25), "medium": (-5.36, -9.38), "boldfilled": (-7.14, -12.5)},
        asset={"light": "df8983be-8f1d-4804-b777-2471318f086a", "medium": "dc08c35d-a52f-4791-83f4-587649db89fb", "boldfilled": "0f5d1312-852b-433d-827f-050f35ba87e6"},
    ),
    "unfold-less-vertical": dict(
        box=(20.83, 33.33, 20.83, 33.33), rotation=0,
        bleed={"light": (-3.57, -6.25), "medium": (-5.36, -9.38), "boldfilled": (-7.14, -12.5)},
        asset={"light": "b4cea969-4ffb-404e-a021-c8286ce7b95f", "medium": "bb46c60d-1005-48ea-b386-3e787596ee8f", "boldfilled": "4e5a9c7a-6c89-4fef-89e8-13e4e106abab"},
    ),
    "double-arrow-left": dict(
        box=(33.33, 25, 33.33, 25), rotation=0,
        bleed={"light": (-6.25, -4.17), "medium": (-9.38, -6.25), "boldfilled": (-12.5, -8.33)},
        asset={"light": "54f71517-2097-48ce-ad70-bd2eac09d2a8", "medium": "9f814191-04b9-4186-aa3e-4d2e6602b0db", "boldfilled": "89dd4975-9f46-4537-9b71-3b8d38ad0909"},
    ),
    "double-arrow-right": dict(
        box=(33.33, 25, 33.33, 25), rotation=0,
        bleed={"light": (-6.25, -4.17), "medium": (-9.38, -6.25), "boldfilled": (-12.5, -8.33)},
        asset={"light": "17b6c2de-f2ae-40d1-bb48-f61551568406", "medium": "51c3a78f-2b19-4317-96f3-093fd2a23abc", "boldfilled": "dc2399c3-b0a7-4eda-8404-23cfc4fe48e2"},
    ),
    "double-arrow-up": dict(
        box=(25, 33.33, 25, 33.33), rotation=0,
        bleed={"light": (-4.17, -6.25), "medium": (-6.25, -9.38), "boldfilled": (-8.33, -12.5)},
        asset={"light": "4aaf2b4d-7f3e-4503-9422-7a40534ce900", "medium": "8ae33c52-5912-4da8-acdd-ae5a9adb73ba", "boldfilled": "03435b68-87fe-487c-a4d3-8d88cb45e1d0"},
    ),
    "double-arrow-down": dict(
        box=(25, 33.33, 25, 33.33), rotation=0,
        bleed={"light": (-4.17, -6.25), "medium": (-6.25, -9.38), "boldfilled": (-8.33, -12.5)},
        asset={"light": "8b999ceb-4fff-4408-95de-eb7d669b231e", "medium": "518de69d-0c6c-4bdc-90fd-c7a2946b5aa8", "boldfilled": "a6db52e8-e4e8-4010-be7e-ffbe42d99f21"},
    ),
    "subdirectory-left": dict(
        box=(25, 25, 25, 25), rotation=0,
        bleed={"light": (-4.17, -4.17), "medium": (-6.25, -6.25), "boldfilled": (-8.33, -8.33)},
        asset={"light": "507e31e4-8558-4c7f-9af2-fd324781be00", "medium": "83a927e4-69cc-4928-a919-0c5ad5558045", "boldfilled": "58caf78c-0742-464a-b5f6-28381acb12c4"},
    ),
    "subdirectory-up": dict(
        box=(25, 25, 25, 25), rotation=0,
        bleed={"light": (-4.17, -4.17), "medium": (-6.25, -6.25), "boldfilled": (-8.33, -8.33)},
        asset={"light": "a432ff13-2b80-4053-aeb4-8b111f9e48d3", "medium": "492703dd-1893-4305-aa6e-b1210213385a", "boldfilled": "758cd3e3-ce14-4018-85e3-03bf2df7e257"},
    ),
    "subdirectory-right": dict(
        box=(25, 25, 25, 25), rotation=0,
        bleed={"light": (-4.17, -4.17), "medium": (-6.25, -6.25), "boldfilled": (-8.33, -8.33)},
        asset={"light": "8d590354-4365-420e-b433-2e1a79920030", "medium": "def6d72c-a8b8-4481-a69d-0b5a5bd650ba", "boldfilled": "c79f936c-6598-43c1-9fd3-b24cbdaaf7a3"},
    ),
    "subdirectory-down": dict(
        box=(25, 25, 25, 25), rotation=0,
        bleed={"light": (-4.17, -4.17), "medium": (-6.25, -6.25), "boldfilled": (-8.33, -8.33)},
        asset={"light": "b14860e0-f6af-4271-8441-ce72ec3993e5", "medium": "0a996c66-2c87-49c7-bddc-b1796aa63086", "boldfilled": "6e1b0272-4eb5-407b-973c-347fd66f4747"},
    ),
    "subdirectory-right-alt": dict(
        box=(25, 25, 25, 25), rotation=0,
        bleed={"light": (-4.17, -4.17), "medium": (-6.25, -6.25), "boldfilled": (-8.33, -8.33)},
        asset={"light": "3d088f94-d6a6-4b3f-a496-844ad4b8f889", "medium": "9d233c3f-ccac-45e0-b972-c5a018666bd8", "boldfilled": "4d3dcd49-3980-405d-9cab-d8996f040431"},
    ),
    "subdirectory-up-alt": dict(
        box=(25, 25, 25, 25), rotation=0,
        bleed={"light": (-4.17, -4.17), "medium": (-6.25, -6.25), "boldfilled": (-8.33, -8.33)},
        asset={"light": "a057ba3b-2554-470b-8dd1-d530460b944f", "medium": "8d9c7934-a923-4d07-b78c-37cbde6d8f87", "boldfilled": "356e8c02-812d-40a0-923e-2be47d9fd4c9"},
    ),
    "subdirectory-left-alt": dict(
        box=(25, 25, 25, 25), rotation=0,
        bleed={"light": (-4.17, -4.17), "medium": (-6.25, -6.25), "boldfilled": (-8.33, -8.33)},
        asset={"light": "a49ddbe9-cc86-4976-8066-b07b2094726e", "medium": "a24631be-e71e-405a-a0e9-d7c6a91a83a0", "boldfilled": "1169577e-427c-4a5c-883d-ab6857b9d49a"},
    ),
    "subdirectory-down-alt": dict(
        box=(25, 25, 25, 25), rotation=0,
        bleed={"light": (-4.17, -4.17), "medium": (-6.25, -6.25), "boldfilled": (-8.33, -8.33)},
        asset={"light": "8fe5ed83-90cd-46fa-a28e-42818c5784e0", "medium": "94bfa0bc-90ce-4d98-a77e-f7cf6f455c0e", "boldfilled": "7cc189c9-1b4d-4ded-9781-134af32e2843"},
    ),
}


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


def compose(slug, spec, group):
    top, right, bottom, left = spec["box"]
    box_x = left / 100 * 24
    box_y = top / 100 * 24
    box_w = 24 - box_x - (right / 100 * 24)
    box_h = 24 - box_y - (bottom / 100 * 24)
    cx, cy = box_x + box_w / 2, box_y + box_h / 2

    rotation = spec["rotation"]
    swapped = rotation in (90, -90, 270, -270)
    pre_w, pre_h = (box_h, box_w) if swapped else (box_w, box_h)

    vert_pct, horiz_pct = spec["bleed"][group]
    eff_w = pre_w * (1 - 2 * horiz_pct / 100)
    eff_h = pre_h * (1 - 2 * vert_pct / 100)
    eff_x = cx - eff_w / 2
    eff_y = cy - eff_h / 2

    body, srcw, srch = fetch(spec["asset"][group])

    inner = (
        f'<svg x="{eff_x:.4f}" y="{eff_y:.4f}" width="{eff_w:.4f}" height="{eff_h:.4f}" '
        f'viewBox="0 0 {srcw:g} {srch:g}" fill="none">{body}</svg>'
    )
    if rotation:
        inner = f'<g transform="rotate({rotation} {cx:.4f} {cy:.4f})">{inner}</g>'

    svg = (
        f'<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">\n'
        f"{inner}\n</svg>\n"
    )
    return recolor(svg)


def main():
    written = []
    for slug, spec in ICONS.items():
        for group, weight_names in WEIGHT_GROUPS.items():
            svg = compose(slug, spec, group)
            names = weight_names if isinstance(weight_names, tuple) else (weight_names,)
            for name in names:
                out_dir = os.path.join(DEST, name.lower())
                os.makedirs(out_dir, exist_ok=True)
                out_path = os.path.join(out_dir, f"{slug}.svg")
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(svg)
                written.append(out_path)
    print(f"Wrote {len(written)} files for {len(ICONS)} icons")


if __name__ == "__main__":
    main()
