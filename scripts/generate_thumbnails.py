#!/usr/bin/env python3
"""
Generate thumbnail images for the gallery view.
Resizes images to max 800px wide at JPEG quality 80.
Updates images.json with a 'thumb' field for each entry.

Run with: /opt/homebrew/bin/python3 scripts/generate_thumbnails.py
"""
import json
from pathlib import Path
from PIL import Image

REPO_ROOT = Path(__file__).parent.parent
IMAGES_DIR = REPO_ROOT / 'images'
THUMBS_DIR = IMAGES_DIR / 'thumbs'
IMAGES_JSON = REPO_ROOT / 'images.json'

MAX_WIDTH = 800
QUALITY = 80


def generate_thumbnail(src_path: Path, dst_path: Path) -> bool:
    """Generate a resized JPEG thumbnail. Returns True if created, False if already exists."""
    if dst_path.exists():
        return False
    with Image.open(src_path) as img:
        img = img.convert('RGB')
        w, h = img.size
        if w > MAX_WIDTH:
            ratio = MAX_WIDTH / w
            img = img.resize((MAX_WIDTH, int(h * ratio)), Image.LANCZOS)
        img.save(dst_path, 'JPEG', quality=QUALITY, optimize=True)
    return True


def main():
    THUMBS_DIR.mkdir(exist_ok=True)

    with open(IMAGES_JSON, encoding='utf-8') as f:
        images = json.load(f)

    created = 0
    skipped = 0

    for entry in images:
        src_name = Path(entry['url']).name
        src_path = IMAGES_DIR / src_name

        if not src_path.exists():
            print(f"  NOT FOUND: {src_name}")
            continue

        thumb_name = src_path.stem + '.jpg'
        dst_path = THUMBS_DIR / thumb_name
        thumb_url = f"images/thumbs/{thumb_name}"

        if generate_thumbnail(src_path, dst_path):
            print(f"  CREATED:  {thumb_name}")
            created += 1
        else:
            print(f"  SKIPPED:  {thumb_name} (already exists)")
            skipped += 1

        entry['thumb'] = thumb_url

    with open(IMAGES_JSON, 'w', encoding='utf-8') as f:
        json.dump(images, f, indent=2, ensure_ascii=False)
        f.write('\n')

    print(f"\nDone: {created} created, {skipped} skipped.")
    print("images.json updated with 'thumb' fields.")


if __name__ == '__main__':
    main()
