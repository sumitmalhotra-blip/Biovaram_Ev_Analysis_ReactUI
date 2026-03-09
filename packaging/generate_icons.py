"""Generate BioVaram icon files from the logo PNG."""
from PIL import Image
import os

logo_path = os.path.join(os.path.dirname(__file__), '..', 'public', 'logo-biovaram.png')
public_dir = os.path.join(os.path.dirname(__file__), '..', 'public')
packaging_dir = os.path.dirname(__file__)

img = Image.open(logo_path)
print(f"BioVaram logo: {img.size}, mode={img.mode}")

# Make the image square by adding padding (centered)
w, h = img.size
max_dim = max(w, h)
square = Image.new("RGBA", (max_dim, max_dim), (0, 0, 0, 0))
offset = ((max_dim - w) // 2, (max_dim - h) // 2)
square.paste(img, offset)
img = square
print(f"Squared to: {img.size}")

# Generate PNG icons at various sizes
for s in [16, 32, 48, 64, 128, 192, 256, 512]:
    resized = img.resize((s, s), Image.LANCZOS)
    outpath = os.path.join(public_dir, f"icon-{s}x{s}.png")
    resized.save(outpath, "PNG")
    fsize = os.path.getsize(outpath)
    print(f"  Created: icon-{s}x{s}.png ({fsize} bytes)")

# Create favicon.ico (multi-size)
ico_small_sizes = [(16, 16), (32, 32), (48, 48), (64, 64)]
ico_small = [img.resize(s, Image.LANCZOS).convert("RGBA") for s in ico_small_sizes]
favicon_path = os.path.join(public_dir, "favicon.ico")
ico_small[-1].save(favicon_path, format="ICO", append_images=ico_small[:-1], sizes=ico_small_sizes)
print(f"  Created: favicon.ico ({os.path.getsize(favicon_path)} bytes)")

# Update PyInstaller .ico with more sizes
ico_all_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
ico_all = [img.resize(s, Image.LANCZOS).convert("RGBA") for s in ico_all_sizes]
biovaram_ico_path = os.path.join(packaging_dir, "biovaram.ico")
ico_all[-1].save(biovaram_ico_path, format="ICO", append_images=ico_all[:-1], sizes=ico_all_sizes)
print(f"  Updated: biovaram.ico ({os.path.getsize(biovaram_ico_path)} bytes)")

print("Done!")
