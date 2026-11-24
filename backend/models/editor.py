"""
Face Editor — SD 1.5 inpainting pipeline for modifying specific face regions.
Optimized for RTX 3050 4GB VRAM.
"""
import os
import time
from PIL import Image, ImageDraw, ImageFilter
import numpy as np

import config


# ── Lazy-loaded pipeline ──────────────────────────────────────────────
_inpaint_pipe = None


def _load_inpainting_pipeline():
    """Load the SD 1.5 inpainting pipeline with low-VRAM opts."""
    global _inpaint_pipe
    if _inpaint_pipe is not None:
        return _inpaint_pipe

    import torch
    from diffusers import StableDiffusionInpaintPipeline, EulerDiscreteScheduler

    # Auto-detect device
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda":
        print(f"[Editor] ✓ CUDA available — {torch.cuda.get_device_name(0)}")
    else:
        print("[Editor] ⚠ CUDA not available — using CPU (slower)")

    dtype = torch.float16 if (config.USE_FP16 and device == "cuda") else torch.float32

    print(f"[Editor] Loading SD 1.5 Inpainting model on {device.upper()} …")
    _inpaint_pipe = StableDiffusionInpaintPipeline.from_pretrained(
        config.SD_INPAINT_MODEL_ID,
        torch_dtype=dtype,
        safety_checker=None,
        requires_safety_checker=False,
    )

    _inpaint_pipe.scheduler = EulerDiscreteScheduler.from_config(
        _inpaint_pipe.scheduler.config
    )

    if config.ENABLE_ATTENTION_SLICING:
        _inpaint_pipe.enable_attention_slicing()
    if config.ENABLE_VAE_SLICING:
        _inpaint_pipe.enable_vae_slicing()
    if device == "cuda" and config.ENABLE_XFORMERS:
        try:
            _inpaint_pipe.enable_xformers_memory_efficient_attention()
            print("[Editor] ✓ xformers enabled")
        except Exception:
            print("[Editor] ⚠ xformers not available")

    if device == "cuda":
        # Aggressive memory offloading for 4GB VRAM
        _inpaint_pipe.enable_model_cpu_offload()
        # Enable VAE tiling to process images in smaller tiles
        try:
            _inpaint_pipe.enable_vae_tiling()
        except AttributeError:
            pass
    else:
        _inpaint_pipe.to(device)

    print(f"[Editor] ✓ Inpainting pipeline loaded on {device.upper()}")
    return _inpaint_pipe


def _mock_edit(image: Image.Image, mask: Image.Image, prompt: str) -> Image.Image:
    """Return a simulated edit for UI development (tints the masked region)."""
    img_array = np.array(image.convert("RGB"))
    mask_array = np.array(mask.convert("L"))

    # Highlight edited region with a slight tint
    overlay = img_array.copy()
    overlay[mask_array > 128] = (
        overlay[mask_array > 128] * 0.7 + np.array([200, 200, 180]) * 0.3
    ).astype(np.uint8)

    result = Image.fromarray(overlay)
    return result


def edit_face(
    image: Image.Image,
    mask: Image.Image,
    prompt: str,
    negative_prompt: str = "",
    steps: int | None = None,
    guidance_scale: float | None = None,
    strength: float | None = None,
) -> tuple[Image.Image, str]:
    """
    Edit a specific face region using inpainting.

    Parameters
    ----------
    image : PIL.Image
        The base face sketch image.
    mask : PIL.Image
        Binary mask — white (255) = region to edit, black (0) = keep.
    prompt : str
        What the edited region should look like.
    negative_prompt : str
        Things to avoid.

    Returns
    -------
    tuple[Image.Image, str]
        (edited image, saved file path)
    """
    steps = steps or config.INFERENCE_STEPS
    guidance_scale = guidance_scale or 10.0   # Higher for inpainting to follow prompt
    strength = strength or 0.95               # High strength = more dramatic edits

    if not config.MOCK_MODE:
        import torch
        if torch.cuda.is_available():
            # Clear cache before inpainting to free up memory from the base model
            torch.cuda.empty_cache()

    if not negative_prompt:
        from utils.prompt_builder import get_negative_prompt
        negative_prompt = get_negative_prompt()

    # ── Resize to model dimensions ────────────────────────────────────
    image = image.convert("RGB").resize(
        (config.IMAGE_WIDTH, config.IMAGE_HEIGHT), Image.LANCZOS
    )
    mask = mask.convert("RGB").resize(
        (config.IMAGE_WIDTH, config.IMAGE_HEIGHT), Image.LANCZOS
    )

    if config.MOCK_MODE:
        result = _mock_edit(image, mask, prompt)
    else:
        pipe = _load_inpainting_pipeline()
        output = pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            image=image,
            mask_image=mask,
            num_inference_steps=steps,
            guidance_scale=guidance_scale,
            strength=strength,
        )
        result = output.images[0]

    # ── Save ──────────────────────────────────────────────────────────
    timestamp = int(time.time() * 1000)
    filename = f"edit_{timestamp}.png"
    filepath = os.path.join(config.OUTPUT_DIR, filename)
    result.save(filepath)

    return result, filepath
