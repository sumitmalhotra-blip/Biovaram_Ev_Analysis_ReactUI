"""Generate icons from the actual BioVaram logo."""
from PIL import Image
import os

public_dir = os.path.join(os.path.dirname(__file__), '..', 'public')
packaging_dir = os.path.dirname(__file__)
logo_path = os.path.join(public_dir, 'logo-biovaram.png')

img = Image.open(logo_path).convert("RGBA")
print(f"Logo: {img.size}")

# Crop to content (remove transparent border)
bbox = img.getbbox()
if bbox:
    img = img.crop(bbox)
    print(f"Cropped to content: {img.size}")

# Make square with padding on a white background
w, h = img.size
max_dim = max(w, h)
padding = int(max_dim * 0.05)  # 5% padding
canvas_size = max_dim + 2 * padding

# Use white background so it looks clean on taskbar/desktop
square = Image.new("RGBA", (canvas_size, canvas_size), (255, 255, 255, 255))
offset_x = (canvas_size - w) // 2
offset_y = (canvas_size - h) // 2
square.paste(img, (offset_x, offset_y), img)  # Use img as mask for transparency
print(f"Final square: {square.size}")

# Generate PNG icons at standard sizes
for s in [16, 32, 48, 64, 128, 192, 256, 512]:
    icon = square.resize((s, s), Image.LANCZOS)
    outpath = os.path.join(public_dir, f"icon-{s}x{s}.png")
    icon.save(outpath, "PNG")
    fsize = os.path.getsize(outpath)
    print(f"  icon-{s}x{s}.png ({fsize} bytes)")

# favicon.ico for browser tab + title bar
sizes_ico = [16, 32, 48, 64]
ico_images = [square.resize((s, s), Image.LANCZOS) for s in sizes_ico]
favicon_path = os.path.join(public_dir, "favicon.ico")
ico_images[-1].save(favicon_path, format="ICO", append_images=ico_images[:-1])
fsize = os.path.getsize(favicon_path)
print(f"  favicon.ico ({fsize} bytes)")

# biovaram.ico for EXE and installer icon
sizes_exe = [16, 32, 48, 64, 128, 256]
exe_images = [square.resize((s, s), Image.LANCZOS) for s in sizes_exe]
ico_path = os.path.join(packaging_dir, "biovaram.ico")
exe_images[-1].save(ico_path, format="ICO", append_images=exe_images[:-1])
fsize = os.path.getsize(ico_path)
print(f"  biovaram.ico ({fsize} bytes)")

print("Done!")
