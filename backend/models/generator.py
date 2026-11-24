"""
Forensic Sketch Generator — Stable Diffusion 1.5 text-to-sketch pipeline.
Optimized for RTX 3050 4GB VRAM (fp16, attention slicing, VAE slicing).
"""
import os
import time
from PIL import Image, ImageDraw, ImageFont
import numpy as np

import config


# ── Lazy-loaded pipeline (None until first call) ──────────────────────
_pipe = None


_device = None

def _get_device():
    """Detect best available device."""
    global _device
    if _device is not None:
        return _device
    import torch
    if torch.cuda.is_available():
        _device = "cuda"
        print(f"[Generator] ✓ CUDA available — {torch.cuda.get_device_name(0)}")
    else:
        _device = "cpu"
        print("[Generator] ⚠ CUDA not available — using CPU (slower)")
    return _device


def _load_pipeline():
    """Load the SD 1.5 pipeline with low-VRAM optimizations."""
    global _pipe
    if _pipe is not None:
        return _pipe

    import torch
    from diffusers import StableDiffusionPipeline, EulerDiscreteScheduler

    device = _get_device()
    # Use fp16 only on CUDA; CPU requires float32
    dtype = torch.float16 if (config.USE_FP16 and device == "cuda") else torch.float32

    print("[Generator] Loading Stable Diffusion …")
    
    # ── Custom Model Check ───────────────────────────────────────────
    custom_path = getattr(config, 'CUSTOM_MODEL_PATH', None)
    if custom_path and os.path.exists(custom_path):
        print(f"[Generator] Using custom checkpoint: {os.path.basename(custom_path)}")
        try:
            _pipe = StableDiffusionPipeline.from_single_file(
                custom_path,
                torch_dtype=dtype,
                use_safetensors=True,
                safety_checker=None,
                requires_safety_checker=False,
            )
        except Exception as e:
            print(f"[Generator] ⚠ Error loading custom checkpoint: {e}")
            print("[Generator] Falling back to standard model...")
            _pipe = None

    if _pipe is None:
        print(f"[Generator] Loading standard model: {config.SD_MODEL_ID}")
        _pipe = StableDiffusionPipeline.from_pretrained(
            config.SD_MODEL_ID,
            torch_dtype=dtype,
            safety_checker=None,
            requires_safety_checker=False,
        )

    # ── Scheduler (Euler — stable & fast) ─────────────────────────────
    # EulerDiscreteScheduler is standard for sketches
    from diffusers import EulerDiscreteScheduler
    _pipe.scheduler = EulerDiscreteScheduler.from_config(
        _pipe.scheduler.config
    )

    # ── Low-VRAM optimizations ────────────────────────────────────────
    if config.ENABLE_ATTENTION_SLICING:
        _pipe.enable_attention_slicing()

    if config.ENABLE_VAE_SLICING:
        _pipe.enable_vae_slicing()

    if device == "cuda" and config.ENABLE_XFORMERS:
        try:
            _pipe.enable_xformers_memory_efficient_attention()
            print("[Generator] ✓ xformers enabled")
        except Exception:
            print("[Generator] ⚠ xformers not available – using default attention")

    if device == "cuda":
        # Aggressive memory offloading for 4GB VRAM
        _pipe.enable_model_cpu_offload()
        # Enable VAE tiling to process images in smaller tiles
        try:
            _pipe.enable_vae_tiling()
        except AttributeError:
            pass
    else:
        _pipe.to(device)

    print(f"[Generator] ✓ Pipeline loaded on {device.upper()}")
    return _pipe


def _generate_mock(prompt: str, negative_prompt: str) -> Image.Image:
    """Return a placeholder sketch image for UI development."""
    img = Image.new("L", (config.IMAGE_WIDTH, config.IMAGE_HEIGHT), color=240)
    draw = ImageDraw.Draw(img)

    # Draw a simple face outline
    cx, cy = config.IMAGE_WIDTH // 2, config.IMAGE_HEIGHT // 2
    # Head oval
    draw.ellipse(
        [cx - 120, cy - 160, cx + 120, cy + 140],
        outline=60, width=2,
    )
    # Eyes
    draw.ellipse([cx - 60, cy - 40, cx - 20, cy - 15], outline=80, width=2)
    draw.ellipse([cx + 20, cy - 40, cx + 60, cy - 15], outline=80, width=2)
    # Nose
    draw.line([(cx, cy - 10), (cx - 10, cy + 30), (cx + 10, cy + 30)], fill=80, width=2)
    # Mouth
    draw.arc([cx - 35, cy + 40, cx + 35, cy + 70], 0, 180, fill=80, width=2)
    # Label
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    draw.text((10, 10), "MOCK MODE", fill=100, font=font)
    draw.text((10, config.IMAGE_HEIGHT - 25), prompt[:60] + "…", fill=120, font=font)

    return img.convert("RGB")


def generate(
    prompt: str,
    negative_prompt: str = "",
    steps: int | None = None,
    seed: int | None = None,
    guidance_scale: float | None = None,
) -> tuple[Image.Image, str]:
    """
    Generate a forensic sketch from a text prompt.

    Returns
    -------
    tuple[Image.Image, str]
        (generated PIL image, saved file path)
    """
    # ── Initialize variables early to avoid UnboundLocalError ───────
    final_image = None
    rng_gen = None
    
    inf_steps = steps or config.INFERENCE_STEPS
    cfg_scale = guidance_scale or config.GUIDANCE_SCALE

    if not negative_prompt:
        from utils.prompt_builder import get_negative_prompt
        negative_prompt = get_negative_prompt()

    # ── Mock mode ─────────────────────────────────────────────────────
    if config.MOCK_MODE:
        final_image = _generate_mock(prompt, negative_prompt)
    else:
        import torch
        pipe = _load_pipeline()
        device = _get_device()
        
        if seed is not None:
            # Explicitly set device for the random generator
            gen_device = "cuda" if device == "cuda" else "cpu"
            rng_gen = torch.Generator(device=gen_device).manual_seed(seed)

        print(f"[Generator] Generating image with {inf_steps} steps...")
        result = pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            num_inference_steps=inf_steps,
            guidance_scale=cfg_scale,
            width=config.IMAGE_WIDTH,
            height=config.IMAGE_HEIGHT,
            generator=rng_gen,
        )
        final_image = result.images[0]

    # ── Save ──────────────────────────────────────────────────────────
    timestamp = int(time.time() * 1000)
    filename = f"sketch_{timestamp}.png"
    filepath = os.path.join(config.OUTPUT_DIR, filename)
    
    if final_image:
        final_image.save(filepath)
    else:
        raise ValueError("Image generation failed — no image produced.")

    return final_image, filepath
