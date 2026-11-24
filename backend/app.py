"""
Flask Backend — AI-Powered Forensic Sketch Generator
API routes for generation, editing, face recognition, auth & history.
"""
import os
import io
import base64
import traceback

from flask import Flask, request, jsonify, send_from_directory, send_file, redirect
from flask_cors import CORS
from flask_login import login_required, current_user
from PIL import Image

import config
from models.database import db, login_manager, init_db
from routes.auth import auth_bp
from routes.history import history_bp, save_to_history
from utils.prompt_builder import build_forensic_prompt, get_negative_prompt, build_inpainting_prompt, auto_detect_regions, build_natural_prompt
from utils.attribute_extractor import extract_attributes
from utils.translator import translate_to_english
from models.generator import generate
from models.editor import edit_face
from models.face_parser import get_region_mask, get_available_regions
from models.recognition import compare, search_in_database
from models.database import History

# ── App setup ─────────────────────────────────────────────────────────
app = Flask(
    __name__,
    static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend"),
    static_url_path="",
)
app.config["SECRET_KEY"] = config.SECRET_KEY
app.config["SQLALCHEMY_DATABASE_URI"] = config.SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = config.SQLALCHEMY_TRACK_MODIFICATIONS
CORS(app)

# ── Initialize DB & Auth ──────────────────────────────────────────────
init_db(app)
app.register_blueprint(auth_bp)
app.register_blueprint(history_bp)


# ══════════════════════════════════════════════════════════════════════
# AUTH PAGE SERVING
# ══════════════════════════════════════════════════════════════════════

@app.route("/login.html")
def serve_login():
    return send_from_directory(app.static_folder, "login.html")


@app.route("/signup.html")
def serve_signup():
    return send_from_directory(app.static_folder, "signup.html")


# ══════════════════════════════════════════════════════════════════════
# STATIC FILE SERVING (protected pages require login)
# ══════════════════════════════════════════════════════════════════════

@app.route("/")
@login_required
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/dashboard.html")
@login_required
def serve_dashboard():
    return send_from_directory(app.static_folder, "dashboard.html")


@app.route("/<page>.html")
@login_required
def serve_page(page):
    if page in ("login", "signup"):
        return send_from_directory(app.static_folder, f"{page}.html")
    return send_from_directory(app.static_folder, f"{page}.html")


# ── Handle Flask-Login redirect for unauthorized API requests ─────────
@login_manager.unauthorized_handler
def unauthorized():
    """Return JSON for API calls, redirect for page requests."""
    if request.path.startswith("/api/"):
        return jsonify({"error": "Authentication required.", "redirect": "/login.html"}), 401
    return redirect("/login.html")


# ══════════════════════════════════════════════════════════════════════
# API — HEALTH
# ══════════════════════════════════════════════════════════════════════

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "mock_mode": config.MOCK_MODE,
        "gpu": "RTX 3050 4GB" if not config.MOCK_MODE else "mock",
    })


# ══════════════════════════════════════════════════════════════════════
# API — GENERATE SKETCH
# ══════════════════════════════════════════════════════════════════════

@app.route("/api/generate", methods=["POST"])
@login_required
def api_generate():
    """
    Generate a forensic sketch from text description.

    Body (JSON):
        description: str       — free-text witness description
        attributes:  dict|None — structured attributes (overrides description parsing)
        seed:        int|None  — reproducible generation
        steps:       int|None  — inference steps (default 20)
    """
    try:
        data = request.get_json(force=True)
        description = data.get("description", "")
        attributes = data.get("attributes", None)
        seed = data.get("seed", None)
        steps = data.get("steps", None)
        language = data.get("language", "en")

        translated_text = None

        # Translate description if not English or if contains non-ASCII characters
        is_marathi = any(ord(c) > 127 for c in description)
        if description and (language != "en" or is_marathi):
            if is_marathi:
                print(f"\n[API] Detected Marathi/Unicode characters in input")
            translated_text, _ = translate_to_english(description, language if not is_marathi else "auto")
            description = translated_text
            print(f"[API] Working with English: '{description}'")

        # Build prompt: Favor full description for higher quality, fallback to attributes
        if description:
            prompt = build_natural_prompt(description)
        elif attributes:
            prompt = build_forensic_prompt(attributes)
        else:
            return jsonify({"error": "Please provide a description or attributes."}), 400

        print(f"[API] Final AI Prompt: '{prompt}'")

        negative_prompt = get_negative_prompt()
        image, filepath = generate(prompt, negative_prompt, steps=steps, seed=seed)

        # Convert to base64 for frontend
        img_base64 = _image_to_base64(image)

        # Save thumbnail and history
        thumbnail = _make_thumbnail(image)
        save_to_history(
            user_id=current_user.id,
            action_type="generate",
            prompt=prompt,
            image_filename=os.path.basename(filepath),
            thumbnail=thumbnail,
        )

        result = {
            "success": True,
            "image": img_base64,
            "prompt_used": prompt,
            "filename": os.path.basename(filepath),
        }
        if translated_text:
            result["translated_text"] = translated_text

        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════════════════
# API — EDIT FACE
# ══════════════════════════════════════════════════════════════════════

@app.route("/api/edit", methods=["POST"])
@login_required
def api_edit():
    """
    Edit a specific face region via inpainting.

    Body (JSON):
        image:        str  — base64 encoded image
        region:       str  — face region: eyes, nose, mouth, jaw, forehead
        modification: str  — what to change (e.g. "longer and sharper")
        steps:        int  — inference steps
    """
    try:
        data = request.get_json(force=True)
        image_b64 = data.get("image", "")
        region = data.get("region", "nose")
        modification = data.get("modification", "")
        steps = data.get("steps", None)
        language = data.get("language", "en")

        if not image_b64:
            return jsonify({"error": "No image provided."}), 400
        if not modification:
            return jsonify({"error": "Please describe the modification."}), 400

        translated_text = None

        # Translate modification if not English
        if language != "en":
            translated_text, _ = translate_to_english(modification, language)
            modification = translated_text

        # Combine regions from dropdown AND auto-detection from text
        detected_regions = auto_detect_regions(modification)
        ui_regions = [r.strip() for r in region.split(",") if r.strip()]
        
        # Merge both sources
        regions = list(set(ui_regions + detected_regions))
        region_label = ",".join(regions) if regions else "face"
        
        if detected_regions:
            print(f"[Editor] Auto-detected regions {detected_regions} from text (UI selection was {ui_regions})")
            print(f"[Editor] Using combined regions: {regions}")

        # Decode image
        image = _base64_to_image(image_b64)

        # Get mask for the region(s)
        mask = get_region_mask(image, regions)

        # Build inpainting prompt
        prompt = build_inpainting_prompt(region_label, modification)
        negative_prompt = get_negative_prompt()

        edited_image, filepath = edit_face(
            image, mask, prompt, negative_prompt, steps=steps
        )

        img_base64 = _image_to_base64(edited_image)
        mask_base64 = _image_to_base64(mask.convert("RGB"))

        # Save to history
        thumbnail = _make_thumbnail(edited_image)
        save_to_history(
            user_id=current_user.id,
            action_type="edit",
            prompt=f"[{region_label}] {modification}",
            image_filename=os.path.basename(filepath),
            thumbnail=thumbnail,
            metadata={"region": region_label},
        )

        result = {
            "success": True,
            "image": img_base64,
            "mask": mask_base64,
            "prompt_used": prompt,
            "region_used": region_label,
            "filename": os.path.basename(filepath),
        }
        if translated_text:
            result["translated_text"] = translated_text

        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════════════════
# API — FACE RECOGNITION
# ══════════════════════════════════════════════════════════════════════

@app.route("/api/recognize", methods=["POST"])
@login_required
def api_recognize():
    """
    Compare two face images for similarity.

    Body (JSON):
        image1: str — base64 encoded first image (sketch)
        image2: str — base64 encoded second image (suspect photo)
    """
    try:
        data = request.get_json(force=True)
        img1_b64 = data.get("image1", "")
        img2_b64 = data.get("image2", "")

        if not img1_b64 or not img2_b64:
            return jsonify({"error": "Both images are required."}), 400

        image1 = _base64_to_image(img1_b64)
        image2 = _base64_to_image(img2_b64)

        result = compare(image1, image2)

        # Save to history
        thumbnail = _make_thumbnail(image1)
        save_to_history(
            user_id=current_user.id,
            action_type="recognize",
            prompt=result.get("message", ""),
            thumbnail=thumbnail,
            metadata={
                "similarity": result.get("similarity", 0),
                "match": result.get("match", False),
            },
        )

        return jsonify({
            "success": True,
            **result,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/search", methods=["POST"])
@login_required
def api_search():
    """
    Search generated sketches against the Suspect Database (colorful photos).
    """
    try:
        data = request.get_json(force=True)
        image_b64 = data.get("image", "")

        if not image_b64:
            return jsonify({"error": "A forensic sketch is required."}), 400

        image = _base64_to_image(image_b64)

        # ── 1. SCAN THE SUSPECTS FOLDER ────────────────────────────────
        if not os.path.exists(config.SUSPECT_DATABASE_DIR):
            os.makedirs(config.SUSPECT_DATABASE_DIR, exist_ok=True)
            
        # Get all image files in the suspect directory
        valid_exts = {".jpg", ".jpeg", ".png", ".webp"}
        candidate_filenames = [
            f for f in os.listdir(config.SUSPECT_DATABASE_DIR) 
            if os.path.splitext(f)[1].lower() in valid_exts
        ]
        
        if not candidate_filenames:
            return jsonify({
                "error": "Suspect database is empty.", 
                "message": "Please add colorful suspect photos to the 'backend/suspects' folder first."
            }), 404

        # Run search (This will use recognition.py)
        # Note: I need to tell recognition.py to look in Suspects instead of Outputs
        from models.recognition import search_in_database as search_suspects
        result = search_suspects(image, candidate_filenames, use_suspect_dir=True)

        if "error" in result:
            return jsonify(result), 400

        # Return full response
        similarity = result.get("similarity", 0.0)
        filename = result.get("filename")
        
        return jsonify({
            "success": True,
            "similarity": similarity,
            "filename": filename,
            "image_url": f"/api/suspects/{filename}",
            "message": result.get("message")
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════════════════
# API — FACE REGIONS INFO
# ══════════════════════════════════════════════════════════════════════

@app.route("/api/regions", methods=["GET"])
def api_regions():
    """Return list of available face regions for editing."""
    return jsonify({"regions": get_available_regions()})


# ══════════════════════════════════════════════════════════════════════
# API — SERVE GENERATED IMAGES
# ══════════════════════════════════════════════════════════════════════

@app.route("/api/outputs/<filename>")
def serve_output(filename):
    return send_from_directory(config.OUTPUT_DIR, filename)


@app.route("/api/suspects/<filename>")
def serve_suspect(filename):
    return send_from_directory(config.SUSPECT_DATABASE_DIR, filename)


# ══════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════

def _image_to_base64(image: Image.Image) -> str:
    """Convert PIL Image to base64 string."""
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def _base64_to_image(b64_string: str) -> Image.Image:
    """Convert base64 string to PIL Image."""
    # Strip data URL prefix if present
    if "," in b64_string:
        b64_string = b64_string.split(",", 1)[1]
    data = base64.b64decode(b64_string)
    return Image.open(io.BytesIO(data))


def _make_thumbnail(image: Image.Image, size: int = 128) -> str:
    """Create a small base64 thumbnail for history cards."""
    thumb = image.copy()
    thumb.thumbnail((size, size))
    buffer = io.BytesIO()
    thumb.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


# ══════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    mode_label = "[MOCK]" if config.MOCK_MODE else "[LIVE]"
    print(f"\n{'=' * 50}")
    print(f"  Forensic Sketch Generator - {mode_label} MODE")
    print(f"  http://localhost:{config.PORT}")
    print(f"{'=' * 50}\n")
    app.run(
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG,
        threaded=True,
        use_reloader=False,   # reloader spawns child process that loses CUDA
    )
