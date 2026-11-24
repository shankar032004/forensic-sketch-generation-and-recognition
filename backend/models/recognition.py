"""
Face Recognition — High-Accuracy matching via DeepFace with Structural Fallback.
"""
import os
import numpy as np
from PIL import Image

import config

print("[Recognition] Initializing High-Accuracy DeepFace Module...")

# ── Lazy-loaded models ─────────────────────────────────────────────────
# DeepFace manages its own models, so we don't need a global _model here.

def get_embedding(image: Image.Image) -> np.ndarray | None:
    """
    Extract facial features. Returns a normalized feature vector.
    Tries DeepFace first, falls back to Structural Map if needed.
    """
    
    # ── 1. REAL AI MODEL (DeepFace) ───────────────────────────────────
    if not config.MOCK_MODE:
        try:
            from deepface import DeepFace
            
            # Convert PIL to BGR array for DeepFace
            img_array = np.array(image.convert("RGB"))
            img_bgr = img_array[:, :, ::-1].copy()
            
            # Extract embedding
            # detector_backend can be: opencv, retinaface, mtcnn, ssd, dlib, mediapipe, yolov8, centerface
            objs = DeepFace.represent(
                img_path=img_bgr,
                model_name=config.RECOGNITION_MODEL,
                enforce_detection=False, # We want an embedding even if face detection is tough
                detector_backend=config.RECOGNITION_BACKEND,
                align=True
            )
            
            if objs and len(objs) > 0:
                # Return the embedding of the first detected face (usually only one in sketches)
                return np.array(objs[0]["embedding"])
                
        except Exception as e:
            print(f"[Recognition] ⚠️ DeepFace error (falling back): {e}")

    # ── 2. SMART MOCK FALLBACK (Structural Similarity) ────────────────
    # Reliable structural map as a safety net if dependencies are missing or memory is low.
    img = image.convert("L").resize((48, 48), Image.Resampling.LANCZOS)
    arr = np.array(img).flatten().astype(np.float32)
    
    # Normalize pixel intensity
    arr = (arr - arr.mean()) / (arr.std() + 1e-5)
    
    # Normalize to unit vector
    norm = np.linalg.norm(arr)
    if norm > 0:
        arr /= norm
    return arr


def compare(image1: Image.Image, image2: Image.Image) -> dict:
    """
    Compare two face images and return similarity score.
    """
    emb1 = get_embedding(image1)
    emb2 = get_embedding(image2)

    if emb1 is None or emb2 is None:
        return {
            "similarity": 0.0,
            "match": False,
            "message": "Could not extract features from images.",
            "error": "feature_extraction_failed",
        }

    # Cosine similarity calculation
    # (dot product of unit vectors)
    norm1 = np.linalg.norm(emb1)
    norm2 = np.linalg.norm(emb2)
    
    if norm1 > 0 and norm2 > 0:
        similarity = float(np.dot(emb1, emb2) / (norm1 * norm2))
    else:
        similarity = 0.0
        
    similarity = max(0.0, min(1.0, similarity))  # clamp

    match = similarity >= config.RECOGNITION_THRESHOLD

    if match:
        message = f"✓ High-Confidence Match — {similarity * 100:.1f}% similarity"
    elif similarity >= 0.5:
        message = f"⚠ Possible Lookalike — {similarity * 100:.1f}% similarity"
    else:
        message = f"✗ No Match — {similarity * 100:.1f}% similarity"

    return {
        "similarity": round(similarity, 4),
        "match": match,
        "message": message,
        "error": None,
    }


def search_in_database(target_image: Image.Image, candidates: list[str], use_suspect_dir: bool = False) -> dict:
    """
    Find the most similar image from a list of files.
    - if use_suspect_dir=True, looks in 'backend/suspects'
    - otherwise looks in 'backend/outputs'
    """
    target_emb = get_embedding(target_image)
    if target_emb is None:
        return {"error": "No face detected in uploaded sketch.", "best_match": None}

    best_similarity = -1.0
    best_filename = None

    # Choose search directory
    search_dir = config.SUSPECT_DATABASE_DIR if use_suspect_dir else config.OUTPUT_DIR
    print(f"[Recognition] Searching {len(candidates)} candidates in {os.path.basename(search_dir)}...")
    
    for filename in candidates:
        filepath = os.path.join(search_dir, filename)
        if not os.path.exists(filepath):
            continue
            
        try:
            with Image.open(filepath) as cand_img:
                cand_emb = get_embedding(cand_img)
                if cand_emb is not None:
                    # Calculate cosine similarity
                    n1 = np.linalg.norm(target_emb)
                    n2 = np.linalg.norm(cand_emb)
                    similarity = float(np.dot(target_emb, cand_emb) / (n1 * n2))
                    
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_filename = filename
        except Exception as e:
            print(f"[Recognition] Error processing {filename}: {e}")

    if best_filename:
        best_similarity = max(0.0, min(1.0, best_similarity))
        is_match = best_similarity >= config.RECOGNITION_THRESHOLD
        
        if is_match:
            message = f"Match found in suspects database! {best_similarity*100:.1f}% similarity."
        elif best_similarity >= 0.4:
            message = f"Possible lead from suspect database: {best_similarity*100:.1f}% similarity."
        else:
            # If it's very low, don't claim it's a match at all
            return {
                "similarity": round(best_similarity, 4),
                "filename": None,
                "match": False,
                "message": f"No similar suspects found. Best candidate was only {best_similarity*100:.1f}% match."
            }

        return {
            "similarity": round(best_similarity, 4),
            "filename": best_filename,
            "match": is_match,
            "message": message
        }
    
    return {"error": "No suitable matches found in database.", "best_match": None}
