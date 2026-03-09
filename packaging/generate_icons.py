"""Generate BioVaram icon files — proper branded 'BV' icons."""
from PIL import Image, ImageDraw, ImageFont
import os

public_dir = os.path.join(os.path.dirname(__file__), '..', 'public')
packaging_dir = os.path.dirname(__file__)


def create_biovaram_icon(size):
    """Create a BV branded icon at given size — dark blue background, blue 'BV' text."""
    img = Image.new('RGBA', (size, size), (15, 23, 42, 255))  # #0f172a slate-900
    draw = ImageDraw.Draw(img)

    # Accent bar at top
    bar_h = max(size // 8, 2)
    draw.rectangle([0, 0, size, bar_h], fill=(96, 165, 250, 255))  # #60a5fa blue-400

    # 'BV' text
    font_size = int(size * 0.55)
    try:
        font = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', font_size)
    except Exception:
        try:
            font = ImageFont.truetype('arial.ttf', font_size)
        except Exception:
            font = ImageFont.load_default()

    text = 'BV'
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (size - tw) // 2
    y = (size - th) // 2 + bar_h // 2
    draw.text((x, y), text, fill=(96, 165, 250, 255), font=font)

    return img


# Generate PNG icons at standard sizes
for s in [16, 32, 48, 64, 128, 192, 256, 512]:
    icon = create_biovaram_icon(s)
    outpath = os.path.join(public_dir, f"icon-{s}x{s}.png")
    icon.save(outpath, "PNG")
    fsize = os.path.getsize(outpath)
    print(f"  icon-{s}x{s}.png ({fsize} bytes)")

# favicon.ico for browser tab
sizes_ico = [16, 32, 48, 64]
ico_images = [create_biovaram_icon(s) for s in sizes_ico]
favicon_path = os.path.join(public_dir, "favicon.ico")
# Save largest first, append smaller — PIL ICO requires this order
ico_images[-1].save(favicon_path, format="ICO", append_images=ico_images[:-1])
fsize = os.path.getsize(favicon_path)
print(f"  favicon.ico ({fsize} bytes)")

# biovaram.ico for EXE and installer icon
sizes_exe = [16, 32, 48, 64, 128, 256]
exe_images = [create_biovaram_icon(s) for s in sizes_exe]
ico_path = os.path.join(packaging_dir, "biovaram.ico")
exe_images[-1].save(ico_path, format="ICO", append_images=exe_images[:-1])
fsize = os.path.getsize(ico_path)
print(f"  biovaram.ico ({fsize} bytes)")

print("Done!")
