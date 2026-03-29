import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

from PIL import Image
import imagehash

try:
    import pillow_heif  # type: ignore

    pillow_heif.register_heif_opener()
except Exception:
    pillow_heif = None  # type: ignore

from image_indexer import build_index


@dataclass(frozen=True)
class ImageMatch:
    label: str
    distance: int
    ref_path: str


def _parse_phash(phash_str: str) -> imagehash.ImageHash:
    # ImageHash supports hex strings directly via hex_to_hash
    return imagehash.hex_to_hash(phash_str)


class ITBlockImageLocator:
    """
    Classifies an uploaded image into:
    - IT Block + floor (if confident)
    - IT Block (floor unknown) (if it matches IT Block but floor not confident)
    - Not IT Block (if it doesn't match IT Block)
    """

    def __init__(
        self,
        index_path: Optional[str] = None,
        it_block_max_distance: int = 12,
        not_it_block_max_distance: int = 12,
        class_margin: int = 3,
        floor_margin: int = 3,
    ):
        self.index_path = index_path or os.path.join(os.path.dirname(__file__), "image_index.json")
        self.it_block_max_distance = it_block_max_distance
        self.not_it_block_max_distance = not_it_block_max_distance
        self.class_margin = class_margin
        self.floor_margin = floor_margin
        self._index = self._load_index()

    def _load_index(self) -> Dict[str, List[Dict[str, str]]]:
        if not os.path.exists(self.index_path):
            return {"items": []}
        with open(self.index_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def is_ready(self) -> bool:
        return bool(self._index.get("items"))

    def reload_from_disk(self) -> int:
        """Reload index JSON from disk (useful when index is rebuilt while server is running)."""
        self._index = self._load_index()
        return len(self._index.get("items", []))

    def rebuild_from_dataset(self, dataset_dir: str) -> int:
        dataset_dir = os.path.abspath(dataset_dir)
        idx = build_index(dataset_dir)
        # persist so reload works across restarts
        import json as _json

        with open(self.index_path, "w", encoding="utf-8") as f:
            _json.dump(idx, f, indent=2)
        self._index = idx
        return len(idx.get("items", []))

    def _compute_phash(self, img: Image.Image) -> imagehash.ImageHash:
        # Normalize some common cases
        img = img.convert("RGB")
        return imagehash.phash(img)

    def _best_matches(self, query_hash: imagehash.ImageHash, top_k: int = 5) -> List[ImageMatch]:
        matches: List[ImageMatch] = []
        for item in self._index.get("items", []):
            try:
                ref_hash = _parse_phash(item["phash"])
                dist = query_hash - ref_hash
                matches.append(ImageMatch(label=item["label"], distance=int(dist), ref_path=item.get("path", "")))
            except Exception:
                continue
        matches.sort(key=lambda m: m.distance)
        return matches[:top_k]

    def classify(self, image_file) -> Dict[str, object]:
        """
        image_file: a file-like object (e.g., Flask's FileStorage stream)
        Returns a dict suitable for JSON response.
        """
        img = Image.open(image_file)
        qh = self._compute_phash(img)
        top = self._best_matches(qh, top_k=10)

        if not top:
            return {
                "verdict": "unknown",
                "message": "Image index is empty or no matches available.",
                "matches": [],
            }

        # Best IT-block match vs best non-IT match
        best_it = next((m for m in top if m.label.startswith("it_block/")), None)
        best_not = next((m for m in top if m.label.startswith("not_it_block/")), None)

        # If we don't have both classes in the dataset, fall back to "best overall"
        if not best_it and not best_not:
            best = top[0]
            return {
                "verdict": "unknown",
                "message": "Training index does not contain it_block/ or not_it_block/ labels. Please organize training images under those folders.",
                "matches": [m.__dict__ for m in top],
            }

        # Decide IT vs Not-IT with distance thresholds + margin
        if best_it and (best_not is None or (best_it.distance + self.class_margin) < best_not.distance):
            if best_it.distance > self.it_block_max_distance:
                return {
                    "verdict": "unknown",
                    "message": "This image does not appear to be from the IT Block.",
                    "matches": [m.__dict__ for m in top],
                }
            chosen = best_it
            chosen_class = "it_block"
        elif best_not:
            if best_not.distance > self.not_it_block_max_distance:
                return {
                    "verdict": "unknown",
                    "message": "This image does not appear to be from the IT Block.",
                    "matches": [m.__dict__ for m in top],
                }
            chosen = best_not
            chosen_class = "not_it_block"
        else:
            chosen = top[0]
            chosen_class = "unknown"

        if chosen_class == "not_it_block":
            return {
                "verdict": "not_it_block",
                "message": "This image does not appear to be from the IT Block.",
                "matches": [m.__dict__ for m in top],
            }

        # IT Block: decide floor if confident
        # Compare best floor-labeled match vs next best different floor/label
        best_floor = chosen.label  # e.g. it_block/floor_1
        second = next((m for m in top if m.label.startswith("it_block/") and m.label != best_floor), None)

        if second and (second.distance - chosen.distance) < self.floor_margin:
            # Too close to call a floor
            return {
                "verdict": "it_block_floor_unknown",
                "message": "This looks like the IT Block, but I can't confidently determine the floor from this image.",
                "it_block": True,
                "floor": None,
                "matches": [m.__dict__ for m in top],
            }

        floor = None
        # Support "floor_0" and any normalized variants
        if best_floor.startswith("it_block/floor_"):
            try:
                floor = int(best_floor.split("it_block/floor_")[1])
            except Exception:
                floor = None

        # Pretty floor names
        floor_name = None
        if floor == 0:
            floor_name = "Ground Floor"
        elif floor == 1:
            floor_name = "First Floor"
        elif floor == 2:
            floor_name = "Second Floor"
        elif floor == 3:
            floor_name = "Third Floor"

        return {
            "verdict": "it_block",
            "message": (
                f"This appears to be the IT Block{'' if floor_name is None else f', {floor_name}'}."
            ),
            "it_block": True,
            "floor": floor,
            "matches": [m.__dict__ for m in top],
        }

