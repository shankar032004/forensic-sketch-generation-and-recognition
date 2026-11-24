import os
import sys

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config
from models import generator

print("--- FSK Model Integration Test ---")
print(f"Current Working Directory: {os.getcwd()}")
print(f"Custom Model Path: {config.CUSTOM_MODEL_PATH}")
print(f"File exists: {os.path.exists(config.CUSTOM_MODEL_PATH)}")

try:
    print("\nAttempting to load pipeline...")
    # This will trigger the _load_pipeline function
    pipe = generator._load_pipeline()
    print("\n✓ SUCCESS: Pipeline loaded!")
    print(f"Model Class: {type(pipe)}")
    
except Exception as e:
    print(f"\n❌ FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n--- Test Complete ---")
