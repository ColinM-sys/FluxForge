"""Ollama-powered agent that expands natural language into detailed image prompts."""
import json
import logging
import random

import httpx

from backend.config import settings
from backend.schemas.generation import ExpandedPrompt

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert Stable Diffusion prompt engineer for PuLID Flux face-preserving image generation.

Given a user's natural language description, generate exactly {count} unique, detailed image prompts.

RULES:
1. Each prompt MUST have a completely different setting, background, and color palette
2. Each prompt MUST describe specific clothing/outfit — always fully clothed, high collar or buttoned shirts
3. NEVER repeat backgrounds, lighting, or color schemes between prompts
4. Include quality tags in every positive prompt
5. Always include "sharp focus, in focus, crisp detailed sharp eyes, hyperrealistic, photorealistic skin, visible ears, 8k masterpiece" at the end of each positive prompt
6. The negative prompt should block: "two faces, multiple faces, duplicate face, twins, two people, vest, body armor, tactical, shirtless, bare chest, blurry, deformed, ugly, watermark, distorted ears"
7. Each scene_description should be a short 5-8 word summary

Return ONLY a JSON array. No markdown, no explanation. Each object must have exactly these keys:
- "scene_description": short summary (5-8 words)
- "positive_prompt": full detailed Stable Diffusion prompt
- "negative_prompt": things to exclude

Example format:
[
  {{
    "scene_description": "Rainy Tokyo rooftop at night",
    "positive_prompt": "cinematic portrait of a man standing on a rainy Tokyo rooftop at night, wearing a dark leather jacket over a black turtleneck, neon city skyline behind, rain falling, dramatic blue and pink neon lighting, sharp focus, in focus, crisp detailed sharp eyes, hyperrealistic, photorealistic skin, visible ears, 8k masterpiece",
    "negative_prompt": "two faces, multiple faces, duplicate face, twins, two people, vest, body armor, tactical, shirtless, bare chest, blurry, deformed, ugly, watermark, distorted ears"
  }}
]"""


async def expand_prompts(description: str, count: int = 5) -> list[ExpandedPrompt]:
    system = SYSTEM_PROMPT.replace("{count}", str(count))

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": f"User request: {description}\n\nGenerate exactly {count} unique prompts as a JSON array:",
                    "system": system,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.9, "num_predict": 4096},
                },
            )

            if resp.status_code != 200:
                logger.error(f"Ollama error: {resp.status_code} {resp.text[:200]}")
                return []

            data = resp.json()
            raw = data.get("response", "")

            # Parse JSON response
            parsed = json.loads(raw)

            # Handle both {"prompts": [...]} and direct [...] formats
            if isinstance(parsed, dict):
                prompts_list = parsed.get("prompts", parsed.get("scenes", parsed.get("results", [])))
                if not prompts_list:
                    # Try to find any list value in the dict
                    for v in parsed.values():
                        if isinstance(v, list):
                            prompts_list = v
                            break
            elif isinstance(parsed, list):
                prompts_list = parsed
            else:
                logger.error(f"Unexpected response format: {type(parsed)}")
                return []

            results = []
            for item in prompts_list[:count]:
                results.append(ExpandedPrompt(
                    scene_description=item.get("scene_description", "Generated scene"),
                    positive_prompt=item.get("positive_prompt", ""),
                    negative_prompt=item.get("negative_prompt",
                        "two faces, multiple faces, duplicate face, twins, two people, "
                        "vest, body armor, tactical, shirtless, bare chest, blurry, "
                        "deformed, ugly, watermark, distorted ears"),
                    seed=random.randint(1, 2147483647),
                ))

            logger.info(f"Agent expanded '{description}' into {len(results)} prompts")
            return results

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Ollama response as JSON: {e}")
            logger.error(f"Raw response: {raw[:500]}")
            return []
        except Exception as e:
            logger.error(f"Agent error: {e}")
            return []
