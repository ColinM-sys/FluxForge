"""POST /api/generate — accept natural language, expand prompts, queue to ComfyUI."""
import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.job import Job, GeneratedImage
from backend.schemas.generation import GenerateRequest, JobOut
from backend.services.agent import expand_prompts
from backend.services.comfy_workflow import build_pulid_flux_workflow
from backend.services.comfy_manager import comfy_manager
from backend.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


async def _run_generation(job_id: int, request: GenerateRequest):
    """Background task that runs the full generation pipeline."""
    from backend.database import async_session

    async with async_session() as db:
        # 1. Update job status to expanding
        job = await db.get(Job, job_id)
        job.status = "expanding"
        await db.commit()

        # 2. Expand prompts via Ollama agent
        prompts = await expand_prompts(request.description, request.count)
        if not prompts:
            job.status = "failed"
            job.error_message = "Failed to expand prompts via Ollama"
            await db.commit()
            return

        job.total_images = len(prompts)
        job.status = "generating"
        await db.commit()

        source_photo = request.source_photo or settings.DEFAULT_SOURCE_PHOTO

        # 3. Generate each image
        for i, prompt in enumerate(prompts):
            prefix = f"fluxforge_{job_id}_{i}"

            workflow = build_pulid_flux_workflow(
                positive_prompt=prompt.positive_prompt,
                negative_prompt=prompt.negative_prompt,
                source_photo=source_photo,
                seed=prompt.seed,
                width=request.width or settings.DEFAULT_WIDTH,
                height=request.height or settings.DEFAULT_HEIGHT,
                pulid_weight=request.pulid_weight or settings.DEFAULT_PULID_WEIGHT,
                filename_prefix=prefix,
            )

            # Try to generate
            filenames = await comfy_manager.generate_one(workflow)

            if filenames:
                for fn in filenames:
                    img = GeneratedImage(
                        job_id=job_id,
                        filename=fn,
                        positive_prompt=prompt.positive_prompt,
                        negative_prompt=prompt.negative_prompt,
                        scene_description=prompt.scene_description,
                        seed=prompt.seed,
                        width=request.width or settings.DEFAULT_WIDTH,
                        height=request.height or settings.DEFAULT_HEIGHT,
                    )
                    db.add(img)

                job.completed_images += 1
                await db.commit()
                logger.info(f"Job {job_id}: {job.completed_images}/{job.total_images} done - {prompt.scene_description}")
            else:
                logger.warning(f"Job {job_id}: Failed to generate image {i} - {prompt.scene_description}")

        # 4. Final status
        job.status = "completed" if job.completed_images > 0 else "failed"
        if job.completed_images < job.total_images and job.completed_images > 0:
            job.status = "completed"
            job.error_message = f"{job.total_images - job.completed_images} images failed"
        await db.commit()
        logger.info(f"Job {job_id} finished: {job.completed_images}/{job.total_images} images")


@router.post("/generate", response_model=JobOut)
async def generate(request: GenerateRequest, db: AsyncSession = Depends(get_db)):
    job = Job(
        description=request.description,
        status="pending",
        total_images=request.count,
        source_photo=request.source_photo or settings.DEFAULT_SOURCE_PHOTO,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Launch generation in background
    asyncio.create_task(_run_generation(job.id, request))

    return job
