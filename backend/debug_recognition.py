import sys
import os

# Set paths to backend
sys.path.append(os.getcwd())

import config
import torch
from PIL import Image

print(f"CUDA Available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")

print("\n--- Attempting to load InsightFace ---")
try:
    from insightface.app import FaceAnalysis
    # Force real load, no bypass
    app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
    app.prepare(ctx_id=-1, det_size=(640, 640))
    print("✓ InsightFace loaded successfully on CPU")
except Exception as e:
    print(f"❌ InsightFace failed to load: {e}")
    import traceback
    traceback.print_exc()
