"""
Face Parser — MediaPipe FaceLandmarker-based region mask generator.
Extracts masks for eyes, nose, mouth, jaw, forehead, and hair regions.
Uses the new MediaPipe Tasks API (compatible with mediapipe >= 0.10.x).
"""
from PIL import Image, ImageDraw
import numpy as np
import os

import config

# ── Lazy-loaded detector ──────────────────────────────────────────────
_face_landmarker = None
_MODEL_PATH = os.path.join(os.path.dirname(__file__), "face_landmarker.task")


def _download_model():
    """Download the face_landmarker model if not present."""
    if os.path.exists(_MODEL_PATH):
        return
    import urllib.request
    url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
    print("[FaceParser] Downloading face_landmarker model...")
    urllib.request.urlretrieve(url, _MODEL_PATH)
    print("[FaceParser] ✓ Model downloaded")


def _load_face_mesh():
    """Load MediaPipe FaceLandmarker (new Tasks API)."""
    global _face_landmarker
    if _face_landmarker is not None:
        return _face_landmarker

    _download_model()

    import mediapipe as mp
    BaseOptions = mp.tasks.BaseOptions
    FaceLandmarker = mp.tasks.vision.FaceLandmarker
    FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode

    options = FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=_MODEL_PATH),
        running_mode=VisionRunningMode.IMAGE,
        num_faces=1,
        min_face_detection_confidence=0.5,
        min_face_presence_confidence=0.5,
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
    )
    _face_landmarker = FaceLandmarker.create_from_options(options)
    print("[FaceParser] ✓ MediaPipe FaceLandmarker loaded")
    return _face_landmarker


# ── MediaPipe landmark index groups ──────────────────────────────────
# Reference: https://github.com/google/mediapipe/blob/master/mediapipe/modules/face_geometry/data/canonical_face_model_uv_visualization.png

_REGION_LANDMARKS = {
    "left_eye":   [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246],
    "right_eye":  [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398],
    "nose":       [1, 2, 3, 4, 5, 6, 197, 195, 168, 166, 59, 75, 97, 99, 240, 235,
                   64, 48, 115, 220, 45, 4, 275, 440, 344, 278, 294, 460, 326, 289],
    "mouth":      [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269,
                   267, 0, 37, 39, 40, 185],
    "jaw":        [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
                   397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
                   172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109],
    "forehead":   [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
                   # Upper face contour
                   109, 67, 103, 54, 21, 162, 127, 234, 93, 132, 58, 172],
    # Hair uses the top contour of the face — extended upward in get_region_mask
    "hair":       [10, 338, 297, 332, 284, 251, 389, 356, 454,
                   234, 127, 162, 21, 54, 103, 67, 109],
}

# Combine both eyes for a single "eyes" region
_REGION_LANDMARKS["eyes"] = _REGION_LANDMARKS["left_eye"] + _REGION_LANDMARKS["right_eye"]


def get_region_mask(
    image: Image.Image,
    region: str | list[str],
    padding: int = 15,
) -> Image.Image:
    """
    Generate a binary mask for one or more face regions.

    Parameters
    ----------
    image : PIL.Image
        The input face image.
    region : str | list[str]
        One or more regions: 'eyes', 'left_eye', 'right_eye', 'nose', 'mouth', 'jaw', 'forehead'.
    padding : int
        Pixels to expand the mask boundary.

    Returns
    -------
    PIL.Image
        Binary mask (white = regions, black = background).
    """
    if isinstance(region, str):
        regions = [region.lower().strip()]
    else:
        regions = [r.lower().strip() for r in region]

    if config.MOCK_MODE:
        # Merge mock masks
        merged_mask = Image.new("L", image.size, 0)
        for r in regions:
            mask = _mock_mask(image, r)
            merged_mask = Image.fromarray(np.maximum(np.array(merged_mask), np.array(mask)))
        return merged_mask

    for r in regions:
        if r not in _REGION_LANDMARKS:
            raise ValueError(
                f"Unknown region '{r}'. "
                f"Valid: {list(_REGION_LANDMARKS.keys())}"
            )

    import mediapipe as mp
    detector = _load_face_mesh()
    img_array = np.array(image.convert("RGB"))
    h, w, _ = img_array.shape

    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_array)
    results = detector.detect(mp_image)
    if not results.face_landmarks:
        raise RuntimeError("No face detected in image.")

    landmarks = results.face_landmarks[0]
    
    # Create combined mask
    final_mask = Image.new("L", (w, h), 0)
    
    for r in regions:
        # Special handling for hair: Expand significantly for long hair support
        if r == "hair":
            # Outer silhouette landmarks for the face region
            face_indices = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 
                            397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 
                            136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]
            face_points = []
            for idx in face_indices:
                lm = landmarks[idx]
                face_points.append((int(lm.x * w), int(lm.y * h)))
            
            # Find face bounds
            xs = [p[0] for p in face_points]
            ys = [p[1] for p in face_points]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            face_w = max_x - min_x
            
            # Create a box covering the top half and sides of the head
            hair_x1 = max(0, min_x - int(face_w * 0.45))
            hair_x2 = min(w, max_x + int(face_w * 0.45))
            hair_y1 = 0
            hair_y2 = min(h, max_y + int(face_w * 0.25))
            
            # Draw the box
            hair_box_mask = Image.new("L", (w, h), 0)
            draw_box = ImageDraw.Draw(hair_box_mask)
            draw_box.rectangle([hair_x1, hair_y1, hair_x2, hair_y2], fill=255)
            
            # Create the face silhouette to subtract (protecting facial features)
            face_mask = Image.new("L", (w, h), 0)
            draw_face = ImageDraw.Draw(face_mask)
            draw_face.polygon(face_points, fill=255)
            
            # DILATE the face_mask to create a "no-fly zone" around features
            # This ensures the AI doesn't modify the face structure/edges
            from PIL import ImageFilter
            for _ in range(8): # 8px buffer to ensure stability
                face_mask = face_mask.filter(ImageFilter.MaxFilter(3))
            
            # Final region_mask for hair = box - padded_face_silhouette
            region_mask = Image.fromarray(
                np.clip(
                    np.array(hair_box_mask).astype(int) - np.array(face_mask).astype(int), 
                    0, 255
                ).astype(np.uint8)
            )
        else:
            # Standard landmark-based region (eyes, nose, mouth, etc.)
            indices = _REGION_LANDMARKS[r]
            points = []
            for idx in indices:
                lm = landmarks[idx]
                x = int(lm.x * w)
                y = int(lm.y * h)
                points.append((x, y))

            # Draw this region onto a temporary mask
            region_mask = Image.new("L", (w, h), 0)
            draw = ImageDraw.Draw(region_mask)
            draw.polygon(points, fill=255)
        
        # Merge with final mask using maximum (logical OR)
        final_mask = Image.fromarray(np.maximum(np.array(final_mask), np.array(region_mask)))

    # Apply padding via dilation (Skip for hair-only to protect face structure)
    # Global dilation would shrink the "face hole" in the hair mask
    is_hair_only = len(regions) == 1 and regions[0] == "hair"
    effective_padding = 0 if is_hair_only else padding
    
    if effective_padding > 0:
        from PIL import ImageFilter
        for _ in range(effective_padding):
            final_mask = final_mask.filter(ImageFilter.MaxFilter(3))

    return final_mask


def _mock_mask(image: Image.Image, region: str) -> Image.Image:
    """Generate an approximate mask for mock/dev mode without MediaPipe."""
    w, h = image.size
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)

    cx, cy = w // 2, h // 2

    region_boxes = {
        "eyes":      [(cx - 80, cy - 55, cx + 80, cy - 5)],
        "left_eye":  [(cx - 80, cy - 50, cx - 15, cy - 10)],
        "right_eye": [(cx + 15, cy - 50, cx + 80, cy - 10)],
        "nose":      [(cx - 30, cy - 15, cx + 30, cy + 45)],
        "mouth":     [(cx - 45, cy + 45, cx + 45, cy + 80)],
        "jaw":       [(cx - 100, cy + 60, cx + 100, cy + 140)],
        "forehead":  [(cx - 90, cy - 140, cx + 90, cy - 50)],
        "hair":      [(cx - 100, 0, cx + 100, cy - 100)],
    }

    boxes = region_boxes.get(region, [(cx - 50, cy - 50, cx + 50, cy + 50)])
    for box in boxes:
        draw.ellipse(box, fill=255)

    return mask


def get_available_regions() -> list[str]:
    """Return list of supported face region names."""
    return list(_REGION_LANDMARKS.keys())
