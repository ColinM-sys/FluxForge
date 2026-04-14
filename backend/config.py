from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # ComfyUI instances
    COMFY_PRIMARY_URL: str = "http://localhost:8188"
    COMFY_SECONDARY_URL: str = "http://10.0.0.21:8189"
    COMFY_INPUT_DIR: str = r"C:\Users\cmcdo\Desktop\ComfyUI\input"
    COMFY_OUTPUT_DIR: str = r"C:\Users\cmcdo\Desktop\ComfyUI\output"

    # Default source photo for PuLID face matching
    DEFAULT_SOURCE_PHOTO: str = "colin_face3.jpg"

    # Ollama for prompt expansion
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:14b"

    # Generation defaults
    DEFAULT_WIDTH: int = 1024
    DEFAULT_HEIGHT: int = 1024
    DEFAULT_STEPS: int = 22
    DEFAULT_GUIDANCE: float = 4.0
    DEFAULT_PULID_WEIGHT: float = 1.0
    DEFAULT_SAMPLER: str = "euler"
    DEFAULT_SCHEDULER: str = "simple"

    # ComfyUI model filenames
    FLUX_UNET: str = "flux1-dev.safetensors"
    FLUX_CLIP_T5: str = "t5xxl_fp16.safetensors"
    FLUX_CLIP_L: str = "clip_l.safetensors"
    FLUX_VAE: str = "ae.safetensors"
    PULID_MODEL: str = "pulid_flux_v0.9.1.safetensors"

    # CUDA crash management
    CUDA_RESTART_THRESHOLD: int = 4
    COMFY_POLL_INTERVAL: float = 2.0
    COMFY_TIMEOUT: float = 300.0

    # FluxForge output (copies from ComfyUI output)
    OUTPUT_DIR: str = str(Path(__file__).parent.parent / "output")

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./fluxforge.db"

    class Config:
        env_file = ".env"


settings = Settings()
