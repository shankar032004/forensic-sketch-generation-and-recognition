import sys
import os

# Set paths to backend
sys.path.append(os.getcwd())

import torch
from PIL import Image
import numpy as np

print(f"CUDA Available: {torch.cuda.is_available()}")

print("\n--- Testing DeepFace Integration ---")
try:
    from deepface import DeepFace
    print("✓ DeepFace imported successfully")
    
    # Check available models
    # We will use 'Facenet512' as it's very accurate but still runs okay on CPU
    model_name = "Facenet512"
    
    # Create a dummy image to test embedding extraction (this might trigger model download)
    dummy_img = np.zeros((224, 224, 3), dtype=np.uint8)
    
    print(f"Testing embedding extraction with {model_name}...")
    # enforce_detection=False so we don't need a real face in the dummy image
    embedding = DeepFace.represent(dummy_img, model_name=model_name, enforce_detection=False)
    
    print(f"✓ Embedding extracted! Vector size: {len(embedding[0]['embedding'])}")
    
except Exception as e:
    print(f"❌ DeepFace test failed: {e}")
    import traceback
    traceback.print_exc()
