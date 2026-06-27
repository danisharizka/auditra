"""Generate centered logo icon + favicon assets from the original Auditra logo."""

from __future__ import annotations

import base64
import io
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "web" / "public"
ASSET_CANDIDATES = [
    ROOT.parent.parent
    / "Users"
    / "Hype"
    / ".cursor"
    / "projects"
    / "c-GALIH-CODING-AUDITRA"
    / "assets"
    / "c__Users_Hype_AppData_Roaming_Cursor_User_workspaceStorage_ffc17569747929d4856205e055d9ad5a_images_image-48943b5a-5746-4089-93d7-ca223336ee76.png",
    PUBLIC / "logo.png",
]

WHITE_THRESH = 248
# Include full magnifying-glass handle; text band starts ~50% height on 1024px master.
ICON_BOTTOM_RATIO = 0.535


def load_source() -> Image.Image:
    for path in ASSET_CANDIDATES:
        if path.exists():
            return Image.open(path).convert("RGB")
    raise FileNotFoundError("Logo source not found")


def is_content_pixel(r: int, g: int, b: int) -> bool:
    return not (r > WHITE_THRESH and g > WHITE_THRESH and b > WHITE_THRESH)


def stack_bbox(img: Image.Image) -> tuple[int, int, int, int]:
    """Bounds of icon + AUDITRA wordmark (full vertical logo stack)."""
    w, h = img.size
    px = img.load()
    xs: list[int] = []
    ys: list[int] = []
    for y in range(h):
        for x in range(w):
            if is_content_pixel(*px[x, y]):
                xs.append(x)
                ys.append(y)

    if not xs:
        return 0, 0, w, h

    left, right = min(xs), max(xs)
    top, bottom = min(ys), max(ys)
    pad_x = int((right - left) * 0.06)
    pad_top = int((bottom - top) * 0.06)
    pad_bottom = int((bottom - top) * 0.14)

    return (
        max(0, left - pad_x),
        max(0, top - pad_top),
        min(w, right + pad_x),
        min(h, bottom + pad_bottom),
    )


def render_header_logo(source: Image.Image, out_height: int, margin_ratio: float = 0.08) -> Image.Image:
    crop = source.crop(stack_bbox(source))
    cw, ch = crop.size
    margin = max(6, int(max(cw, ch) * margin_ratio))
    canvas = Image.new("RGBA", (cw + margin * 2, ch + margin * 2), (255, 255, 255, 255))
    canvas.paste(crop, (margin, margin))
    scale = out_height / canvas.size[1]
    nw = max(1, int(canvas.size[0] * scale))
    return canvas.resize((nw, out_height), Image.Resampling.LANCZOS)


def icon_bbox(img: Image.Image) -> tuple[int, int, int, int]:
    """Tight rectangular bounds of the mark (A + magnifying glass), excluding wordmark."""
    w, h = img.size
    px = img.load()
    icon_bottom = int(h * ICON_BOTTOM_RATIO)

    xs: list[int] = []
    ys: list[int] = []
    for y in range(icon_bottom):
        for x in range(w):
            if is_content_pixel(*px[x, y]):
                xs.append(x)
                ys.append(y)

    if not xs:
        side = int(min(w, h) * 0.42)
        ox = (w - side) // 2
        oy = int(h * 0.17)
        return ox, oy, ox + side, oy + side

    left, right = min(xs), max(xs)
    top, bottom = min(ys), max(ys)

    pad_x = int((right - left) * 0.1)
    pad_y = int((bottom - top) * 0.1)

    return (
        max(0, left - pad_x),
        max(0, top - pad_y),
        min(w, right + pad_x),
        min(h, bottom + pad_y),
    )


def render_icon(source: Image.Image, out_size: int, margin_ratio: float = 0.1) -> Image.Image:
    crop = source.crop(icon_bbox(source))
    cw, ch = crop.size
    inner = max(cw, ch)
    margin = max(4, int(inner * margin_ratio))
    canvas_side = inner + margin * 2
    canvas = Image.new("RGBA", (canvas_side, canvas_side), (255, 255, 255, 255))

    scale = inner / max(cw, ch)
    nw, nh = max(1, int(cw * scale)), max(1, int(ch * scale))
    resized = crop.resize((nw, nh), Image.Resampling.LANCZOS)
    ox = (canvas_side - nw) // 2
    oy = (canvas_side - nh) // 2
    canvas.paste(resized, (ox, oy))
    return canvas.resize((out_size, out_size), Image.Resampling.LANCZOS)


def write_favicon_svg(icon_128: Image.Image) -> None:
    buf = io.BytesIO()
    icon_128.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">'
        '<rect width="128" height="128" rx="22" fill="#ffffff"/>'
        f'<image href="data:image/png;base64,{b64}" x="10" y="10" width="108" height="108" '
        'preserveAspectRatio="xMidYMid meet"/>'
        "</svg>"
    )
    (PUBLIC / "favicon.svg").write_text(svg, encoding="utf-8")


def main() -> None:
    PUBLIC.mkdir(parents=True, exist_ok=True)
    (PUBLIC / "icons").mkdir(exist_ok=True)

    source = load_source()
    source.save(PUBLIC / "logo.png", "PNG")

    icon_256 = render_icon(source, 256, margin_ratio=0.1)
    icon_256.save(PUBLIC / "logo-icon.png", "PNG")

    render_header_logo(source, 112).save(PUBLIC / "logo-header.png", "PNG")
    render_header_logo(source, 144).save(PUBLIC / "logo-header@2x.png", "PNG")

    render_icon(source, 192, margin_ratio=0.1).save(PUBLIC / "icons" / "icon-192.png", "PNG")
    render_icon(source, 512, margin_ratio=0.1).save(PUBLIC / "icons" / "icon-512.png", "PNG")

    fav32 = render_icon(source, 32, margin_ratio=0.08)
    fav32.save(PUBLIC / "favicon-32.png", "PNG")

    fav16 = render_icon(source, 16, margin_ratio=0.06)
    fav48 = render_icon(source, 48, margin_ratio=0.08)
    fav16.save(
        PUBLIC / "favicon.ico",
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48)],
        append_images=[fav32, fav48],
    )

    render_icon(source, 180, margin_ratio=0.1).save(PUBLIC / "apple-touch-icon.png", "PNG")
    write_favicon_svg(render_icon(source, 128, margin_ratio=0.1))

    box = icon_bbox(source)
    stack = stack_bbox(source)
    print("Assets written to", PUBLIC)
    print("Icon bbox:", box, "size:", box[2] - box[0], box[3] - box[1])
    print("Header bbox:", stack, "size:", stack[2] - stack[0], stack[3] - stack[1])


if __name__ == "__main__":
    main()
