"""Build a contact sheet PNG from a folder of illustrations, for eyeball QA."""

import pathlib
import re
import subprocess
import sys

CELL_W, CELL_H = 320, 240
PAD = 14


def inner(svg_text):
    return re.sub(r"^.*?<svg[^>]*>", "", svg_text, flags=re.S).replace("</svg>", "")


def build(folder, out_png, cols=4):
    files = sorted(pathlib.Path(folder).glob("*.svg"))
    if not files:
        sys.exit(f"no svgs in {folder}")
    rows = (len(files) + cols - 1) // cols
    w = cols * (CELL_W + PAD) + PAD
    h = rows * (CELL_H + PAD) + PAD
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
             f'viewBox="0 0 {w} {h}"><rect width="{w}" height="{h}" fill="#ffffff"/>']
    for i, f in enumerate(files):
        cx = PAD + (i % cols) * (CELL_W + PAD)
        cy = PAD + (i // cols) * (CELL_H + PAD)
        parts.append(f'<g transform="translate({cx} {cy})">{inner(f.read_text())}</g>')
    parts.append("</svg>")
    tmp = pathlib.Path(out_png).with_suffix(".sheet.svg")
    tmp.write_text("".join(parts), encoding="utf-8")
    subprocess.run(["rsvg-convert", "-o", str(out_png), str(tmp)], check=True)
    tmp.unlink()
    print(f"{out_png}  ({len(files)} tiles, {cols}x{rows})")
    for f in files:
        print("  ", f.name)


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 4)
