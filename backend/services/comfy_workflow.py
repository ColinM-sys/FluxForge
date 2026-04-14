"""Build ComfyUI API-format workflow JSON for PuLID Flux generation."""
import random
from backend.config import settings


def build_pulid_flux_workflow(
    positive_prompt: str,
    negative_prompt: str,
    source_photo: str = None,
    seed: int = None,
    width: int = None,
    height: int = None,
    pulid_weight: float = None,
    steps: int = None,
    guidance: float = None,
    filename_prefix: str = "fluxforge",
) -> dict:
    source_photo = source_photo or settings.DEFAULT_SOURCE_PHOTO
    seed = seed or random.randint(1, 2147483647)
    width = width or settings.DEFAULT_WIDTH
    height = height or settings.DEFAULT_HEIGHT
    pulid_weight = pulid_weight if pulid_weight is not None else settings.DEFAULT_PULID_WEIGHT
    steps = steps or settings.DEFAULT_STEPS
    guidance = guidance if guidance is not None else settings.DEFAULT_GUIDANCE

    workflow = {
        "10": {
            "class_type": "UNETLoader",
            "inputs": {"unet_name": settings.FLUX_UNET, "weight_dtype": "default"},
        },
        "11": {
            "class_type": "DualCLIPLoader",
            "inputs": {
                "clip_name1": settings.FLUX_CLIP_T5,
                "clip_name2": settings.FLUX_CLIP_L,
                "type": "flux",
            },
        },
        "12": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": settings.FLUX_VAE},
        },
        "13": {
            "class_type": "PulidFluxModelLoader",
            "inputs": {"pulid_file": settings.PULID_MODEL},
        },
        "14": {
            "class_type": "PulidFluxEvaClipLoader",
            "inputs": {},
        },
        "15": {
            "class_type": "PulidFluxInsightFaceLoader",
            "inputs": {"provider": "CUDA"},
        },
        "16": {
            "class_type": "LoadImage",
            "inputs": {"image": source_photo},
        },
        "17": {
            "class_type": "ApplyPulidFlux",
            "inputs": {
                "model": ["10", 0],
                "pulid_flux": ["13", 0],
                "eva_clip": ["14", 0],
                "face_analysis": ["15", 0],
                "image": ["16", 0],
                "weight": pulid_weight,
                "start_at": 0.0,
                "end_at": 1.0,
                "fusion": "mean",
                "fusion_weight_max": 1.0,
                "fusion_weight_min": 0.0,
                "train_step": 1000,
                "use_gray": True,
            },
        },
        "18": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": positive_prompt, "clip": ["11", 0]},
        },
        "19": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": negative_prompt,
                "clip": ["11", 0],
            },
        },
        "20": {
            "class_type": "FluxGuidance",
            "inputs": {"conditioning": ["18", 0], "guidance": guidance},
        },
        "21": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1},
        },
        "22": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["17", 0],
                "positive": ["20", 0],
                "negative": ["19", 0],
                "latent_image": ["21", 0],
                "seed": seed,
                "steps": steps,
                "cfg": 1.0,
                "sampler_name": settings.DEFAULT_SAMPLER,
                "scheduler": settings.DEFAULT_SCHEDULER,
                "denoise": 1.0,
            },
        },
        "23": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["22", 0], "vae": ["12", 0]},
        },
        "24": {
            "class_type": "SaveImage",
            "inputs": {"images": ["23", 0], "filename_prefix": filename_prefix},
        },
    }

    return {"prompt": workflow}
