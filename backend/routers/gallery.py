"""Gallery and image serving endpoints."""
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.config import settings

router = APIRouter(prefix="/api")


@router.get("/gallery")
async def list_gallery_images():
    output_dir = Path(settings.OUTPUT_DIR)
    if not output_dir.exists():
        return []

    images = []
    for f in sorted(output_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
            images.append({
                "filename": f.name,
                "size_kb": round(f.stat().st_size / 1024),
                "modified": f.stat().st_mtime,
            })
    return images


@router.get("/gallery/{filename}")
async def get_image(filename: str):
    filepath = Path(settings.OUTPUT_DIR) / filename
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(str(filepath), media_type="image/png")


@router.get("/source-photos")
async def list_source_photos():
    input_dir = Path(settings.COMFY_INPUT_DIR)
    if not input_dir.exists():
        return []

    photos = []
    for f in input_dir.iterdir():
        if f.suffix.lower() in (".png", ".jpg", ".jpeg"):
            photos.append({"filename": f.name, "size_kb": round(f.stat().st_size / 1024)})
    return photos
