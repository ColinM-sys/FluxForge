"""Manage ComfyUI instances — submit jobs, poll completion, handle CUDA crashes."""
import asyncio
import json
import logging
import shutil
import subprocess
from pathlib import Path
from dataclasses import dataclass, field

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ComfyInstance:
    name: str
    url: str
    generation_count: int = 0
    is_busy: bool = False
    is_healthy: bool = True
    comfy_dir: str = ""
    extra_args: list = field(default_factory=list)


class ComfyManager:
    def __init__(self):
        self.instances = [
            ComfyInstance(
                name="RTX 4090",
                url=settings.COMFY_PRIMARY_URL,
                comfy_dir=r"C:\Users\cmcdo\Desktop\ComfyUI",
                extra_args=["--disable-cuda-malloc"],
            ),
        ]
        # Add secondary GPU if configured
        if settings.COMFY_SECONDARY_URL:
            self.instances.append(
                ComfyInstance(
                    name="RTX 3090",
                    url=settings.COMFY_SECONDARY_URL,
                    comfy_dir=r"C:\Users\Colin\Desktop\ComfyUI",
                    extra_args=["--disable-cuda-malloc", "--port", "8189", "--listen", "0.0.0.0"],
                )
            )
        self._client = httpx.AsyncClient(timeout=30.0)

    def get_available_instance(self) -> ComfyInstance | None:
        for inst in self.instances:
            if not inst.is_busy and inst.is_healthy:
                return inst
        return None

    async def health_check(self, instance: ComfyInstance) -> bool:
        try:
            resp = await self._client.get(f"{instance.url}/system_stats", timeout=5.0)
            instance.is_healthy = resp.status_code == 200
            return instance.is_healthy
        except Exception:
            instance.is_healthy = False
            return False

    async def submit(self, workflow_json: dict, instance: ComfyInstance) -> str | None:
        try:
            resp = await self._client.post(
                f"{instance.url}/prompt",
                json=workflow_json,
                timeout=10.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("node_errors"):
                    logger.error(f"Node errors: {data['node_errors']}")
                    return None
                return data.get("prompt_id")
            else:
                logger.error(f"Submit failed: {resp.status_code} {resp.text[:200]}")
                return None
        except Exception as e:
            logger.error(f"Submit error: {e}")
            instance.is_healthy = False
            return None

    async def poll_completion(self, prompt_id: str, instance: ComfyInstance) -> dict | None:
        elapsed = 0.0
        while elapsed < settings.COMFY_TIMEOUT:
            try:
                resp = await self._client.get(
                    f"{instance.url}/history/{prompt_id}",
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if prompt_id in data:
                        entry = data[prompt_id]
                        status = entry.get("status", {})
                        status_str = status.get("status_str", "")

                        if status_str == "success" and status.get("completed"):
                            instance.generation_count += 1
                            return entry

                        if status_str == "error":
                            messages = status.get("messages", [])
                            for msg in messages:
                                if msg[0] == "execution_error":
                                    err = msg[1].get("exception_message", "")
                                    logger.error(f"ComfyUI error on {instance.name}: {err}")
                                    if "CUDA" in err:
                                        instance.is_healthy = False
                                    return None
            except Exception as e:
                logger.warning(f"Poll error: {e}")

            await asyncio.sleep(settings.COMFY_POLL_INTERVAL)
            elapsed += settings.COMFY_POLL_INTERVAL

        logger.error(f"Timeout waiting for {prompt_id} on {instance.name}")
        return None

    def get_output_files(self, prompt_id: str, history_entry: dict) -> list[str]:
        filenames = []
        outputs = history_entry.get("outputs", {})
        for node_id, node_output in outputs.items():
            if "images" in node_output:
                for img in node_output["images"]:
                    filenames.append(img["filename"])
        return filenames

    async def copy_output_to_gallery(self, filename: str, instance: ComfyInstance) -> str | None:
        if instance == self.instances[0]:
            # Local 4090 — just copy from ComfyUI output to FluxForge output
            src = Path(settings.COMFY_OUTPUT_DIR) / filename
            dst = Path(settings.OUTPUT_DIR) / filename
            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(src), str(dst))
                return filename
        else:
            # Remote 3090 — download via API
            try:
                resp = await self._client.get(
                    f"{instance.url}/view",
                    params={"filename": filename, "type": "output"},
                    timeout=30.0,
                )
                if resp.status_code == 200:
                    dst = Path(settings.OUTPUT_DIR) / filename
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    dst.write_bytes(resp.content)
                    return filename
            except Exception as e:
                logger.error(f"Failed to download {filename} from {instance.name}: {e}")
        return None

    async def needs_restart(self, instance: ComfyInstance) -> bool:
        return (
            instance.generation_count >= settings.CUDA_RESTART_THRESHOLD
            or not instance.is_healthy
        )

    async def restart(self, instance: ComfyInstance):
        logger.info(f"Restarting ComfyUI on {instance.name}...")
        instance.is_busy = True

        # Interrupt and clear queue
        try:
            await self._client.post(f"{instance.url}/interrupt", timeout=5.0)
            await self._client.post(
                f"{instance.url}/queue",
                json={"clear": True},
                timeout=5.0,
            )
        except Exception:
            pass

        if instance == self.instances[0]:
            # Local 4090
            subprocess.run(
                ["powershell.exe", "-Command",
                 "Get-Process python -ErrorAction SilentlyContinue | "
                 "Where-Object {$_.WS -gt 1000000000} | Stop-Process -Force"],
                capture_output=True,
            )
            await asyncio.sleep(5)
            args = ["python", "main.py"] + instance.extra_args
            subprocess.Popen(
                ["powershell.exe", "-Command",
                 f"Start-Process cmd -ArgumentList '/k','cd /d {instance.comfy_dir} && {' '.join(args)}'"],
            )
        else:
            # Remote 3090 via SSH
            subprocess.run(
                ["ssh", "Colin@10.0.0.21",
                 "Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force; "
                 "Start-Sleep 5; schtasks /Run /TN ComfyUI3090 2>&1 | Out-Null"],
                capture_output=True,
            )

        # Wait for ComfyUI to come back up
        for _ in range(60):
            await asyncio.sleep(2)
            if await self.health_check(instance):
                break

        instance.generation_count = 0
        instance.is_busy = False
        instance.is_healthy = True
        logger.info(f"ComfyUI restarted on {instance.name}")

    async def generate_one(
        self, workflow_json: dict, instance: ComfyInstance = None
    ) -> list[str] | None:
        if instance is None:
            instance = self.get_available_instance()
        if instance is None:
            logger.error("No available ComfyUI instance")
            return None

        # Check if restart needed before generation
        if await self.needs_restart(instance):
            await self.restart(instance)

        instance.is_busy = True
        try:
            prompt_id = await self.submit(workflow_json, instance)
            if not prompt_id:
                return None

            history = await self.poll_completion(prompt_id, instance)
            if not history:
                return None

            filenames = self.get_output_files(prompt_id, history)
            copied = []
            for fn in filenames:
                result = await self.copy_output_to_gallery(fn, instance)
                if result:
                    copied.append(result)

            return copied
        finally:
            instance.is_busy = False


# Singleton
comfy_manager = ComfyManager()
