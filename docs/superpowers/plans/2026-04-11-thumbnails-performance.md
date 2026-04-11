# Thumbnail Performance Optimization — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce gallery page load from ~94MB to ~3–4MB by generating and serving thumbnail images instead of full-resolution camera JPEGs.

**Architecture:** A Python script reads all images in `images/`, generates reduced copies (max 800px, JPEG 80%) in `images/thumbs/`, and updates `images.json` with a `thumb` field. The gallery in `index.html` uses the thumbnail; the detail view keeps the original.

**Tech Stack:** Python 3 + Pillow (available at `/opt/homebrew/bin/python3`), vanilla JS, static JSON.

---

### Task 1: Create `scripts/generate_thumbnails.py`

**Files:**
- Create: `scripts/generate_thumbnails.py`

- [ ] **Step 1: Create the script**

Create `scripts/generate_thumbnails.py` with this content:

```python
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
```

- [ ] **Step 2: Run the script**

```bash
/opt/homebrew/bin/python3 scripts/generate_thumbnails.py
```

Expected output (one line per image):
```
  CREATED:  FotosCavet00001.jpg
  CREATED:  FotosCavet00004.jpg
  ...
  CREATED:  Expo00074.jpg

Done: 22 created, 0 skipped.
images.json updated with 'thumb' fields.
```

- [ ] **Step 3: Verify thumbnails were created and are small**

```bash
ls -lh images/thumbs/ | head -10
```

Expected: 22 files, each between 50KB and 200KB (not 5–7MB).

- [ ] **Step 4: Verify `images.json` has `thumb` field**

```bash
head -5 images.json
```

Expected output:
```json
[
  { "id": "FotosCavet00001", "url": "images/FotosCavet00001.jpg", "titulo": "FotosCavet00001", "thumb": "images/thumbs/FotosCavet00001.jpg" },
```

- [ ] **Step 5: Commit**

```bash
git add scripts/generate_thumbnails.py images.json images/thumbs/
git commit -m "feat: add thumbnail generation script and generated thumbs"
```

---

### Task 2: Update `index.html` to use thumbnails in gallery

**Files:**
- Modify: `index.html` (function `renderGallery`, lines ~239–258)

- [ ] **Step 1: Replace image resolution in `renderGallery`**

In `index.html`, find this block inside `renderGallery()`:

```js
      cardsData.forEach(card => {
        const imageUrl = getImageUrl(card.photoId);
        if (!imageUrl) return;
```

Replace it with:

```js
      cardsData.forEach(card => {
        const img = imagesData.find(i => i.id === card.photoId);
        if (!img) return;
        const imageUrl = img.thumb || img.url;
```

No other changes. `showDetail()` continues using `getImageUrl()` which returns the full-resolution `url`.

- [ ] **Step 2: Open the gallery in browser and verify**

Open `index.html` locally (e.g. with Live Server or `open index.html`) and:
- Gallery cards load fast with thumbnails
- Clicking a card opens the detail view with the full-resolution image
- All 22 species cards appear

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "feat: use thumbnail images in gallery view"
```

---

### Task 3: Final verification and push

- [ ] **Step 1: Check total size difference**

```bash
du -sh images/thumbs/
du -sh images/*.JPG images/*.jpg 2>/dev/null | tail -1
```

Expected: `thumbs/` should be ~2–4MB total vs ~94MB for originals.

- [ ] **Step 2: Run script a second time to verify idempotency**

```bash
/opt/homebrew/bin/python3 scripts/generate_thumbnails.py
```

Expected: all images show `SKIPPED` (not recreated), `images.json` unchanged.

- [ ] **Step 3: Push to GitHub Pages**

```bash
git push
```

Visit `https://cavecavet.github.io/exposicions` and verify gallery loads fast.
