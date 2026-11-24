import torch
import sys
import os

print(f"Python version: {sys.version}")
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"CUDA device count: {torch.cuda.device_count()}")
    print(f"Current device: {torch.cuda.current_device()}")
    print(f"Device name: {torch.cuda.get_device_name(0)}")
else:
    print("CUDA is NOT available to PyTorch.")
    # Check for common reasons
    if sys.platform == "win32":
        print("Checking for NVIDIA drivers...")
        # Check if C:\Windows\System32\nvcuda.dll exists
        if os.path.exists(r"C:\Windows\System32\nvcuda.dll"):
            print("nvcuda.dll found in System32.")
        else:
            print("nvcuda.dll NOT found. NVIDIA drivers might be missing or not in PATH.")

try:
    import onnxruntime as ort
    print(f"ONNX Runtime version: {ort.__version__}")
    print(f"ONNX Runtime providers: {ort.get_available_providers()}")
except ImportError:
    print("ONNX Runtime NOT installed.")
