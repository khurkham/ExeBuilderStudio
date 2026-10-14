"""Image helpers for platform-specific application icons."""
from pathlib import Path
from PIL import Image, ImageOps


def prepare_icon(source: str, target: Path, platform: str) -> Path | None:
    """Convert a supplied image to ICO (Windows) or ICNS (macOS)."""
    if not source:
        return None
    src = Path(source).expanduser().resolve()
    if not src.is_file():
        raise ValueError(f"Icon image does not exist: {src}")
    target.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as image:
        image = ImageOps.exif_transpose(image).convert("RGBA")
        size = 1024 if platform == "macos" else 256
        image.thumbnail((size, size), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        canvas.alpha_composite(image, ((size-image.width)//2, (size-image.height)//2))
        if platform == "windows":
            canvas.save(target, format="ICO", sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
        elif platform == "macos":
            canvas.save(target, format="ICNS")
        else:
            raise ValueError("Unknown icon target platform.")
    return target
