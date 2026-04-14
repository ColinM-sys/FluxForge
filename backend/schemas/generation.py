from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class GenerateRequest(BaseModel):
    description: str
    count: int = 5
    source_photo: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    pulid_weight: Optional[float] = None


class ExpandedPrompt(BaseModel):
    scene_description: str
    positive_prompt: str
    negative_prompt: str
    seed: int


class JobOut(BaseModel):
    id: int
    description: str
    status: str
    total_images: int
    completed_images: int
    source_photo: str
    created_at: datetime
    error_message: Optional[str] = None
    images: list["ImageOut"] = []

    class Config:
        from_attributes = True


class ImageOut(BaseModel):
    id: int
    filename: str
    positive_prompt: str
    scene_description: Optional[str] = None
    seed: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
