import os
import sys
# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

import torch
from models.generator import generate
from config import OUTPUT_DIR

print("Testing Image Generation...")
prompt = "A high-quality forensic sketch of a man with short hair and a thin mustache, police sketch style"
negative_prompt = "color, photo, blurry, low quality"

try:
    image, filepath = generate(prompt, negative_prompt, steps=5) # 5 steps for quick test
    print(f"Success! Image saved to: {filepath}")
    if torch.cuda.is_available():
        print(f"Used GPU: {torch.cuda.get_device_name(0)}")
    else:
        print("Warning: Used CPU instead of GPU")
except Exception as e:
    print(f"Error during generation: {e}")
    import traceback
    traceback.print_exc()
