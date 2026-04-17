"""Generate a placeholder app icon for Vessel Ops AI.

Renders a 1024×1024 master PNG (navy→teal gradient rounded square with a
stylised ship's helm wheel in warm amber) plus every size Tauri expects,
including `icon.icns` and multi-size `icon.ico`. Run once; check the output
into `src-tauri/icons/` until a real designed icon replaces it.

    python3 scripts/generate_placeholder_icon.py
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "src-tauri" / "icons"
MASTER = 1024
CORNER = int(MASTER * 0.22)

NAVY_TOP = (9, 20, 48)
NAVY_MID = (16, 42, 82)
TEAL = (28, 78, 108)
AMBER = (242, 176, 68)
AMBER_BRIGHT = (255, 208, 120)
WHITE = (240, 246, 252)


def rounded_mask(size: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size, size), radius=radius, fill=255)
    return mask


def radial_gradient(size: int, inner: tuple[int, int, int], outer: tuple[int, int, int]) -> Image.Image:
    img = Image.new("RGB", (size, size), outer)
    px = img.load()
    cx = cy = size / 2
    max_r = math.hypot(cx, cy)
    for y in range(size):
        for x in range(size):
            r = math.hypot(x - cx, y - cy) / max_r
            r = min(1.0, r)
            px[x, y] = (
                int(inner[0] + (outer[0] - inner[0]) * r),
                int(inner[1] + (outer[1] - inner[1]) * r),
                int(inner[2] + (outer[2] - inner[2]) * r),
            )
    return img


def draw_helm(img: Image.Image) -> None:
    d = ImageDraw.Draw(img, "RGBA")
    size = img.width
    cx = cy = size / 2

    outer_r = size * 0.36
    rim_w = int(size * 0.045)
    inner_r = size * 0.13
    hub_r = size * 0.055
    handle_r_start = outer_r
    handle_r_end = outer_r + size * 0.075
    handle_w = int(size * 0.04)

    # Outer rim
    d.ellipse(
        (cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r),
        outline=WHITE + (235,),
        width=rim_w,
    )
    # Inner rim
    d.ellipse(
        (cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r),
        outline=WHITE + (235,),
        width=int(rim_w * 0.65),
    )

    # Spokes (8) + 8 handles radiating out of the rim
    for i in range(8):
        angle = math.radians(-90 + i * 45)
        dx, dy = math.cos(angle), math.sin(angle)
        # Spoke from inner rim to outer rim
        d.line(
            (cx + dx * inner_r, cy + dy * inner_r, cx + dx * outer_r, cy + dy * outer_r),
            fill=WHITE + (230,),
            width=int(rim_w * 0.8),
        )
        # Outer handle
        is_north = i == 0
        fill = AMBER_BRIGHT if is_north else WHITE + (235,)
        if not is_north:
            fill = WHITE + (230,)
        d.line(
            (cx + dx * handle_r_start, cy + dy * handle_r_start,
             cx + dx * handle_r_end,   cy + dy * handle_r_end),
            fill=fill if is_north else WHITE + (230,),
            width=handle_w,
        )
        # Handle tip cap
        tip_r = handle_w * 0.6
        tip_cx = cx + dx * handle_r_end
        tip_cy = cy + dy * handle_r_end
        d.ellipse(
            (tip_cx - tip_r, tip_cy - tip_r, tip_cx + tip_r, tip_cy + tip_r),
            fill=AMBER_BRIGHT if is_north else WHITE + (235,),
        )

    # Centre hub (amber)
    d.ellipse(
        (cx - hub_r, cy - hub_r, cx + hub_r, cy + hub_r),
        fill=AMBER,
        outline=AMBER_BRIGHT,
        width=int(size * 0.006),
    )


def build_master() -> Image.Image:
    bg = radial_gradient(MASTER, NAVY_MID, NAVY_TOP)
    # Subtle teal glow band from bottom-centre
    glow = Image.new("RGBA", (MASTER, MASTER), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse(
        (-MASTER * 0.2, MASTER * 0.45, MASTER * 1.2, MASTER * 1.6),
        fill=TEAL + (150,),
    )
    glow = glow.filter(ImageFilter.GaussianBlur(radius=60))
    bg = Image.alpha_composite(bg.convert("RGBA"), glow)

    draw_helm(bg)

    # Round the corners
    mask = rounded_mask(MASTER, CORNER)
    final = Image.new("RGBA", (MASTER, MASTER), (0, 0, 0, 0))
    final.paste(bg, (0, 0), mask)
    return final


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    master = build_master()

    master.save(OUT / "icon.png", format="PNG")

    sizes = {
        "32x32.png": 32,
        "128x128.png": 128,
        "128x128@2x.png": 256,
        "icon_256x256.png": 256,
        "icon_512x512.png": 512,
    }
    for name, s in sizes.items():
        master.resize((s, s), Image.LANCZOS).save(OUT / name, format="PNG")

    # Multi-size .ico for Windows
    master.save(
        OUT / "icon.ico",
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )

    # .icns for macOS (Pillow ships an ICNS writer)
    icns_sizes = [(16, 16), (32, 32), (64, 64), (128, 128), (256, 256), (512, 512), (1024, 1024)]
    master.save(OUT / "icon.icns", format="ICNS", sizes=icns_sizes)

    print("Wrote placeholder icons to", OUT)


if __name__ == "__main__":
    main()
