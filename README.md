# 🔍 AI-Powered Forensic Sketch Generation & Recognition Platform

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1.0-black?logo=flask)](https://flask.palletsprojects.com/)
[![Diffusers](https://img.shields.io/badge/AI-Stable%20Diffusion%201.5-orange)](https://huggingface.co/docs/diffusers)
[![DeepFace](https://img.shields.io/badge/Recognition-DeepFace%20(Facenet512)-green)](https://github.com/serengil/deepface)
[![MediaPipe](https://img.shields.io/badge/Parsing-MediaPipe%20FaceLandmarker-blueviolet)](https://developers.google.com/mediapipe)

An end-to-end **AI-Powered Forensic Sketch Generation, Facial Inpainting, and Suspect Recognition System** built with **Flask**, **Stable Diffusion 1.5**, **MediaPipe FaceLandmarker**, **DeepFace (`Facenet512`)**, and **SQLite**—optimized to run smoothly on consumer **4GB VRAM GPUs (e.g., NVIDIA RTX 3050)** as well as in CPU/Mock development mode.

---

## ✨ Key Capabilities

- **🎨 Text-to-Forensic Sketch (`POST /api/generate`):** Generates realistic pencil/composite forensic sketches from natural witness descriptions or structured facial attributes using **Stable Diffusion v1.5** (or a custom `.safetensors` checkpoint) with `EulerDiscreteScheduler` and low-VRAM optimizations (`FP16`, attention slicing, VAE slicing/tiling, CPU offloading).
- **🌐 Multilingual Input Support (Marathi / Unicode → English):** Automatically detects non-English / Unicode descriptions and translates them to English via `deep-translator` before prompt engineering.
- **✏️ Region-Targeted Facial Editing (`POST /api/edit`):** Uses **MediaPipe FaceLandmarker** (`face_landmarker.task`) to compute precise binary masks for `eyes`, `left_eye`, `right_eye`, `nose`, `mouth`, `jaw`, `forehead`, and `hair` (with automatic region detection from edit text), then applies **Stable Diffusion Inpainting**.
- **🔎 1:1 Face Comparison & 1:N Suspect Database Search (`POST /api/recognize`, `POST /api/search`):** Computes **DeepFace (`Facenet512` + `opencv`)** embeddings and cosine similarity scores (threshold `0.65`) against a suspect photo gallery (`backend/suspects/`), with a lightweight structural similarity fallback.
- **🔐 User Authentication & Action History:** Session-based authentication with **Flask-Login** (`Werkzeug` password hashing) and paginated SQLite history tracking (`generate`, `edit`, `recognize`) with base64 thumbnails.

---

## 📂 Project Structure

```text
forensic-sketch-generation-and-recognition/
├── README.md                          # Overview & quick-start run instructions
├── PROJECT_REPORT.md                  # Detailed technical & architectural report
├── .gitignore                         # Excludes fsk.db, backend/outputs/, logs, __pycache__
├── .env.example                       # Environment variable template
├── test_gen.py                        # Generation smoke test script
├── backend/
│   ├── app.py                         # Flask API server & static frontend host (Port 5000)
│   ├── config.py                      # Paths, model IDs, 4GB VRAM settings & DB config
│   ├── requirements.txt               # Full AI & web dependencies
│   ├── check_cuda.py                  # CUDA / PyTorch GPU verification utility
│   ├── debug_recognition.py           # Recognition debugging helper
│   ├── test_deepface.py               # DeepFace embedding smoke test
│   ├── test_my_model.py               # Custom checkpoint verification script
│   ├── verify_integration.py          # Integration check script
│   ├── models/
│   │   ├── database.py                # SQLAlchemy ORM (User, History) & Flask-Login setup
│   │   ├── generator.py               # SD 1.5 text-to-sketch + mock mode
│   │   ├── editor.py                  # SD 1.5 inpainting pipeline + mock mode
│   │   ├── face_parser.py             # MediaPipe FaceLandmarker region masking
│   │   ├── recognition.py             # DeepFace Facenet512 & cosine similarity search
│   │   └── face_landmarker.task       # MediaPipe FaceLandmarker model asset
│   ├── routes/
│   │   ├── auth.py                    # /api/auth/* (signup, login, logout, me)
│   │   └── history.py                 # /api/history/* (list, get, delete)
│   ├── utils/
│   │   ├── attribute_extractor.py     # Structured facial attribute extraction
│   │   ├── prompt_builder.py          # Forensic & inpainting prompt engineering
│   │   └── translator.py              # Multilingual translation to English
│   └── suspects/                      # Sample suspect photo gallery for 1:N search
└── frontend/
    ├── index.html                     # Sketch Generator workspace
    ├── editor.html                    # Region-based Facial Inpainting Editor
    ├── recognition.html               # 1:1 & Suspect DB Recognition UI
    ├── dashboard.html                 # User History Dashboard
    ├── login.html / signup.html       # Authentication pages
    ├── css/style.css                  # UI styles
    └── js/                            # Client-side API integrations
```

---

## 🚀 Run Commands (Quick Start)

### 1. Create Virtual Environment & Install Dependencies

#### Windows (PowerShell)
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> **UI-only / Mock Mode (No GPU or PyTorch required):**
> Set `MOCK_MODE = True` in `backend/config.py`, then install lightweight dependencies:
> ```powershell
> pip install flask flask-cors flask-sqlalchemy flask-login deep-translator Pillow numpy scipy
> ```

### 2. Run the Server
```powershell
cd backend
$env:SECRET_KEY="your_secret_key_here"
python app.py
```

- Access the web app at **`http://localhost:5000`** (redirects unauthenticated visitors to `/login.html`).
- SQLite database (`backend/fsk.db`) and `backend/outputs/` / `backend/uploads/` folders are created automatically at runtime.

---

## ⚙️ Low-VRAM Hardware Profile (`backend/config.py`)

| Setting | Value | Purpose |
| :--- | :--- | :--- |
| Resolution | `512 × 512` | Fits comfortably in 4GB VRAM |
| Precision | `FP16` (`USE_FP16 = True` on CUDA) | Halves model memory footprint |
| Memory Optimizations | `enable_attention_slicing()`, `enable_vae_slicing()`, `enable_vae_tiling()`, `enable_model_cpu_offload()` | Prevents OOM on RTX 3050 4GB |
| Scheduler / Steps | `EulerDiscreteScheduler`, `20` steps, `CFG 7.5` | Fast sketch synthesis |
| Reloader | `use_reloader=False` (`DEBUG = False`) | Prevents child process CUDA loss |

---

## 📄 Detailed Technical Report

For architecture diagrams, database schemas, endpoint payloads, masking logic, and security notes, see **[PROJECT_REPORT.md](./PROJECT_REPORT.md)**.
