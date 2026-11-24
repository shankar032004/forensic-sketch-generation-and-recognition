import torch
from diffusers import StableDiffusionPipeline
from PIL import Image
import os

# 1. Path to your downloaded model
# Since your file is 4.26 GB, it is a FULL CHECKPOINT (not just a LoRA).
model_path = "my_trained_model.safetensors"

print(f"Loading checkpoint '{model_path}'... this will take a moment.")

# 2. Load the model directly from the single file
# This is used for standard Stable Diffusion .safetensors files
try:
    pipe = StableDiffusionPipeline.from_single_file(
        model_path, 
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        use_safetensors=True
    )
    print("✓ Model loaded successfully!")
except Exception as e:
    print(f"Error loading model: {e}")
    # Fallback if from_single_file fails (might need to install specific dependencies)
    exit()

# 4. Move to GPU if you have one
if torch.cuda.is_available():
    pipe.to("cuda")
    print("✓ Running on NVIDIA GPU")
else:
    pipe.to("cpu")
    print("! Running on CPU (this will be slow)")

# 5. Generate an image
# For a full fine-tuned checkpoint, use the prompt style it was trained on.
prompt = "A forensic sketch of a person, highly detailed, pencil lead drawing style, clean white background"
negative_prompt = "color, blurry, low quality, distorted, photo, digital art"

print(f"Generating image for prompt: '{prompt}'...")
# Using 30 steps for better quality on a full checkpoint
image = pipe(prompt, negative_prompt=negative_prompt, num_inference_steps=30).images[0]

# 6. Save the result
image.save("my_test_output.png")
print("✓ Done! Look for 'my_test_output.png' in your folder.")
