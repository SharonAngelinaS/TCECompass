import argparse
import json
import os

from image_indexer import build_index


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--dataset-dir",
        default=os.path.join(os.path.dirname(__file__), "..", "data", "image_training"),
    )
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "image_index.json"))
    args = ap.parse_args()

    dataset_dir = os.path.abspath(args.dataset_dir)
    out_path = os.path.abspath(args.out)

    idx = build_index(dataset_dir)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(idx, f, indent=2)

    print(f"Wrote {len(idx['items'])} items to {out_path}")


if __name__ == "__main__":
    main()

