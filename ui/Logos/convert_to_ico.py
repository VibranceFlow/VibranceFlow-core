import sys
from pathlib import Path
from PIL import Image

def convert_png_to_ico():
    target_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    current_dir = Path('.')
    png_files = list(current_dir.glob('*.png'))

    if not png_files:
        print("No .png files found in the current directory.")
        sys.exit(0)

    print(f"Found {len(png_files)} .png file(s). Starting conversion...\n")

    for png_path in png_files:
        try:
            img = Image.open(png_path)
            ico_path = png_path.with_suffix('.ico')
            img.save(ico_path, format='ICO', sizes=target_sizes)
            print(f"Success: '{png_path.name}' -> '{ico_path.name}'")
        except Exception as e:
            print(f"Error converting '{png_path.name}': {e}")

if __name__ == "__main__":
    convert_png_to_ico()
