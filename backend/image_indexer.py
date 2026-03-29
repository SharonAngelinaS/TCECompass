import os
from typing import Dict, List

from PIL import Image

try:
    import pillow_heif  # type: ignore

    pillow_heif.register_heif_opener()
except Exception:
    # HEIC support is optional at runtime; without it, HEIC files will fail to open.
    pillow_heif = None  # type: ignore

import imagehash


SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}


def infer_label_from_path(rel_path: str) -> str:
    """
    Expected dataset layout (recommended):
      data/image_training/
        it_block/
          floor_0/
          floor_1/
          floor_2/
          floor_3/
        not_it_block/
          misc/
    """
    parts = rel_path.replace("\\", "/").split("/")
    if len(parts) < 2:
        return "unknown"
    # Normalize folder names like "floor 0" -> "floor_0"
    cls = parts[0].strip().lower().replace(" ", "_")
    sub = parts[1].strip().lower().replace(" ", "_")
    return f"{cls}/{sub}"


def build_index(dataset_dir: str) -> Dict[str, List[Dict[str, str]]]:
    items: List[Dict[str, str]] = []
    for root, _, files in os.walk(dataset_dir):
        for fn in files:
            ext = os.path.splitext(fn)[1].lower()
            if ext not in SUPPORTED_EXTS:
                continue
            full_path = os.path.join(root, fn)
            rel_path = os.path.relpath(full_path, dataset_dir).replace("\\", "/")
            label = infer_label_from_path(rel_path)
            try:
                img = Image.open(full_path).convert("RGB")
                ph = imagehash.phash(img)
                items.append({"label": label, "phash": str(ph), "path": rel_path})
            except Exception as e:
                print(f"Skipping {full_path}: {e}")

    return {"items": items, "dataset_dir": dataset_dir.replace("\\", "/")}


def has_any_images(dataset_dir: str) -> bool:
    for root, _, files in os.walk(dataset_dir):
        for fn in files:
            if os.path.splitext(fn)[1].lower() in SUPPORTED_EXTS:
                return True
    return False

