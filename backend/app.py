from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from io import BytesIO
import mimetypes
import os
import re
import time
from datetime import datetime

from PIL import Image

try:
    import pillow_heif  # type: ignore

    pillow_heif.register_heif_opener()
except Exception:
    pass

from data_processor import DataProcessor
from llm_service import LLMService
from image_locator import ITBlockImageLocator
from image_indexer import has_any_images


# -----------------------------
# BLEU SCORE
# -----------------------------
def _compute_bleu(reference_text: str, candidate_text: str) -> float:

    if not reference_text or not reference_text.strip():
        return 0.0

    try:
        import nltk

        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', quiet=True)

        from nltk.translate.bleu_score import sentence_bleu

        ref_tokens = reference_text.split()
        cand_tokens = candidate_text.split()

        if not ref_tokens or not cand_tokens:
            return 0.0

        score = sentence_bleu(
            [ref_tokens],
            cand_tokens,
            weights=(0.25, 0.25, 0.25, 0.25)
        )

        return round(float(score), 4)

    except Exception:
        return 0.0


app = Flask(__name__)
CORS(app)


# -----------------------------
# IMAGE SERVING ROUTE
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

IMAGE_DIR = os.path.abspath(
    os.path.join(BASE_DIR, "..", "data", "image_training")
)


def _safe_image_path(relative_path: str):
    """Resolve a path under IMAGE_DIR and block traversal."""
    safe_rel = relative_path.replace("\\", "/").lstrip("/")
    full = os.path.normpath(os.path.join(IMAGE_DIR, safe_rel))
    root = os.path.normpath(IMAGE_DIR)
    try:
        if os.path.commonpath([full, root]) != root:
            return None
    except ValueError:
        return None
    return full if os.path.isfile(full) else None


@app.route("/static/<path:filename>")
def serve_image(filename):
    """
    Serve training images. HEIC/HEIF are converted to JPEG because most browsers
    cannot decode HEIC in <img>.
    """
    full_path = _safe_image_path(filename)
    if not full_path:
        return jsonify({"error": "Not found"}), 404

    ext = os.path.splitext(full_path)[1].lower()
    if ext in (".heic", ".heif"):
        try:
            img = Image.open(full_path).convert("RGB")
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=88)
            buf.seek(0)
            return send_file(buf, mimetype="image/jpeg")
        except Exception as e:
            print("IMAGE SERVE ERROR (HEIC):", e)
            return jsonify({"error": "Could not read image"}), 500

    mt, _ = mimetypes.guess_type(full_path)
    return send_file(full_path, mimetype=mt or "application/octet-stream")


# -----------------------------
# INITIALIZE SERVICES
# -----------------------------
data_processor = DataProcessor()
llm_service = LLMService(data_processor)
image_locator = ITBlockImageLocator()


metrics = {
    "text_chat": {"count": 0, "total_time": 0.0},
    "image_chat": {"count": 0, "total_time": 0.0},
}


# -----------------------------
# VOICE NORMALIZATION
# -----------------------------
def normalize_voice_to_text_query(query: str) -> str:

    corrections = [
        (r"\bsee\s+lab\b", "SSE lab"),
        (r"\bessay\s+lab\b", "SSE lab"),
        (r"\bs\.s\.e\.?\s+lab\b", "SSE lab"),
        (r"\bgautham\b", "Gowtham"),
    ]

    result = query

    for pattern, repl in corrections:
        result = re.sub(pattern, repl, result, flags=re.IGNORECASE)

    return result


# -----------------------------
# TEXT CHAT
# -----------------------------
@app.route("/api/chat", methods=["POST"])
def chat():

    start_time = time.time()

    try:

        data = request.get_json()

        user_query = data.get("message", "")

        if not user_query:
            return jsonify({"error": "No message provided"}), 400

        user_query = normalize_voice_to_text_query(user_query)

        context_data = data_processor.get_relevant_context(user_query)

        response = llm_service.generate_response(user_query, context_data)

        response_time = (time.time() - start_time) * 1000

        metrics["text_chat"]["count"] += 1
        metrics["text_chat"]["total_time"] += response_time

        return jsonify({
            "response": response
        })

    except Exception as e:

        print("TEXT CHAT ERROR:", e)

        return jsonify({"error": str(e)}), 500


# -----------------------------
# HEALTH CHECK
# -----------------------------
@app.route("/api/health", methods=["GET"])
def health():

    if not image_locator.is_ready():
        image_locator.reload_from_disk()

    return jsonify({
        "status": "healthy"
    })


# -----------------------------
# IMAGE CHAT
# -----------------------------
@app.route("/api/image-chat", methods=["POST"])
def image_chat():

    start_time = time.time()

    try:

        if "image" not in request.files:
            return jsonify({"error": "No image uploaded"}), 400

        img = request.files["image"]

        result = image_locator.classify(img.stream)

        # Add dataset image URL
        if result.get("matches"):
            ref_path = result["matches"][0]["ref_path"]

            result["image_url"] = (
                "http://127.0.0.1:5000/static/" + ref_path
            )

        response_time = (time.time() - start_time) * 1000

        result["response_time_ms"] = round(response_time, 2)

        metrics["image_chat"]["count"] += 1
        metrics["image_chat"]["total_time"] += response_time

        return jsonify(result)

    except Exception as e:

        print("IMAGE CHAT ERROR:", e)

        return jsonify({"error": str(e)}), 500


# -----------------------------
# RUN SERVER
# -----------------------------
if __name__ == "__main__":

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )