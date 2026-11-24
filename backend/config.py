"""
Central configuration for the Forensic Sketch Generator.
Optimized for RTX 3050 4GB VRAM.
"""
import os
import secrets

# ── Paths ──────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
SUSPECT_DATABASE_DIR = os.path.join(BASE_DIR, "suspects")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SUSPECT_DATABASE_DIR, exist_ok=True)

# ── Model IDs ──────────────────────────────────────────────────────────
SD_MODEL_ID = "runwayml/stable-diffusion-v1-5"
SD_INPAINT_MODEL_ID = "runwayml/stable-diffusion-inpainting"
INSIGHTFACE_MODEL = "buffalo_l"

# Set this to your local .safetensors file to use your custom trained model
# If this file doesn't exist, it will fallback to the standard SD_MODEL_ID
CUSTOM_MODEL_PATH = os.path.join(BASE_DIR, "my_trained_model.safetensors")

# ── Generation Settings (optimized for 4GB VRAM) ──────────────────────
IMAGE_WIDTH = 512
IMAGE_HEIGHT = 512
INFERENCE_STEPS = 20
GUIDANCE_SCALE = 7.5
USE_FP16 = True
ENABLE_ATTENTION_SLICING = True
ENABLE_VAE_SLICING = True
ENABLE_XFORMERS = True          # auto-fallback if not installed

# ── Scheduler ──────────────────────────────────────────────────────────
SCHEDULER = "DPMSolverMultistep"   # fast & high quality

# ── Face Recognition ───────────────────────────────────────────────────
# Threshold for "match": Facenet512 typically matches > 0.65
RECOGNITION_THRESHOLD = 0.65      
RECOGNITION_MODEL = "Facenet512"  # Alternatives: VGG-Face, OpenFace, Facenet
RECOGNITION_BACKEND = "opencv"    # Detector: opencv, retinaface, mtcnn

# ── Server ─────────────────────────────────────────────────────────────
HOST = "0.0.0.0"
PORT = 5000
DEBUG = False   # Must be False for GPU inference (reloader kills CUDA)

# ── Auth & Database ────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(16)
SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'fsk.db')}"
SQLALCHEMY_TRACK_MODIFICATIONS = False

# ── Mock Mode (set to True to skip model loading during UI dev) ────────
MOCK_MODE = False   # Real AI generation enabled
